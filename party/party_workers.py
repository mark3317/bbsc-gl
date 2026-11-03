"""Bounded disk and per-peer socket workers; no game/state lock held during I/O."""
import copy,itertools,queue,socket,struct,threading,time

class DurableWriter:
    def __init__(self,write):
        self.write=write;self.queue=queue.Queue(256);self.lock=threading.Lock()
        self.serial=0;self.done=0;self.error=None;self.writes=0
        self.thread=threading.Thread(target=self.run,daemon=True);self.thread.start()
    def submit(self,path,value):
        snapshot=copy.deepcopy(value)
        with self.lock:
            if self.error:raise OSError(self.error)
            self.serial+=1;ticket=self.serial
            try:self.queue.put_nowait((ticket,path,snapshot))
            except queue.Full:
                self.error='durable queue full';raise OSError(self.error)
            return ticket
    def ready(self,ticket):
        with self.lock:
            if self.error:raise OSError(self.error)
            return self.done>=ticket
    def run(self):
        while True:
            item=self.queue.get()
            if item is None:return
            batch=[item];stop=False
            # Coalesce cumulative snapshots, preserving ACK-after-durability.
            time.sleep(.003)
            for _ in range(127):
                try:extra=self.queue.get_nowait()
                except queue.Empty:break
                if extra is None:stop=True;break
                batch.append(extra)
            latest={path:value for _,path,value in batch}
            try:
                for path,value in latest.items():self.write(path,value);self.writes+=1
                with self.lock:self.done=batch[-1][0]
            except OSError as error:
                with self.lock:self.error=f'durable write failed: {type(error).__name__}'
                return
            if stop:return
    def close(self):
        if self.thread.is_alive():
            try:self.queue.put(None,timeout=1)
            except queue.Full:return
            self.thread.join(3)

class PeerSender:
    def __init__(self,endpoint,source,stop,on_error,allowed=lambda:True):
        self.endpoint=endpoint;self.source=source;self.stop=stop;self.on_error=on_error;self.allowed=allowed
        self.queue=queue.PriorityQueue(256);self.queued=set();self.lock=threading.Lock()
        self.serial=itertools.count();self.socket=None
        self.thread=threading.Thread(target=self.run,daemon=True);self.thread.start()
    def put(self,raw,priority):
        with self.lock:
            if raw in self.queued:return
            try:self.queue.put_nowait((priority,next(self.serial),raw));self.queued.add(raw)
            except queue.Full:self.on_error('outbound peer queue full')
    def run(self):
        while not self.stop.is_set():
            try:_,_,raw=self.queue.get(timeout=.05)
            except queue.Empty:continue
            try:
                if not self.allowed():continue
                if self.socket is None:
                    self.socket=socket.create_connection(self.endpoint,timeout=.08,source_address=(self.source,0))
                    self.socket.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
                self.socket.sendall(struct.pack('<I',len(raw))+raw)
            except OSError:
                if self.socket:self.socket.close();self.socket=None
                # Protocol-level retries retain original IDs, never authorize failover.
            finally:
                with self.lock:self.queued.discard(raw)
        if self.socket:self.socket.close();self.socket=None
    def close(self):
        sock=self.socket
        if sock:
            try:sock.shutdown(socket.SHUT_RDWR)
            except OSError:pass
        self.thread.join(1)
