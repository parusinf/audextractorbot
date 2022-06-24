from multiprocessing import Pool


class AsyncFactory:
    def __init__(self, func, cb_func):
        self.func = func
        self.cb_func = cb_func
        self.pool = Pool(1)

    def call(self, *args, **kwargs):
        self.pool.apply_async(self.func, args, kwargs, self.cb_func)

    def wait(self):
        self.pool.close()
        self.pool.join()

    def stop(self):
        self.pool.close()
        self.pool.terminate()
