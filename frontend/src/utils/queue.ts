
type Task<T> = () => Promise<T>;

class RequestQueue {
  private queue: { task: Task<any>; resolve: (value: any) => void; reject: (reason?: any) => void }[] = [];
  private processing = 0;
  private concurrency = 1; // 严格串行，确保最稳健的加载，避免浏览器解码器崩溃

  constructor(concurrency = 1) {
    this.concurrency = concurrency;
  }

  add<T>(task: Task<T>): Promise<T> {
    return new Promise((resolve, reject) => {
      this.queue.push({ task, resolve, reject });
      this.process();
    });
  }

  // Add retry logic with exponential backoff
  async addWithRetry<T>(task: Task<T>, retries = 3, delay = 1000): Promise<T> {
      return this.add(async () => {
          let lastError;
          for (let i = 0; i < retries; i++) {
              try {
                  return await task();
              } catch (err) {
                  lastError = err;
                  // Only retry on network errors or timeout, not on unmount
                  if (err instanceof Error && err.message === "Component unmounted") {
                      throw err;
                  }
                  console.warn(`Task failed, retrying (${i + 1}/${retries})...`, err);
                  await new Promise(r => setTimeout(r, delay * Math.pow(2, i)));
              }
          }
          throw lastError;
      });
  }

  private async process() {
    if (this.processing >= this.concurrency || this.queue.length === 0) {
      return;
    }

    this.processing++;
    const { task, resolve, reject } = this.queue.shift()!;

    try {
      const result = await task();
      resolve(result);
    } catch (error) {
      reject(error);
    } finally {
      this.processing--;
      this.process();
    }
  }
}

// 导出单例，确保全局共享同一个队列
export const assetQueue = new RequestQueue(1);
