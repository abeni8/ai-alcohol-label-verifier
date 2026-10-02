/** Bounded browser-owned queue. Results do not survive closing or refreshing the tab. */
export async function runQueue(items, work, onUpdate, { concurrency = 2, signal } = {}) {
  if (!Number.isInteger(concurrency) || concurrency < 1) throw new Error('Invalid concurrency');
  let next = 0;
  const outcomes = Array(items.length);
  async function worker() {
    while (next < items.length && !signal?.aborted) {
      const index = next++;
      const item = items[index];
      onUpdate(index, { state: 'processing', error: '', result: null });
      try {
        const result = await work(item, signal);
        const update = signal?.aborted ? { state: 'cancelled', error: 'Stopped before the result was accepted.', result: null } : { state: 'completed', result, error: '' };
        outcomes[index] = update;
        onUpdate(index, update);
      } catch (error) {
        const update = { state: signal?.aborted || error.name === 'AbortError' ? 'cancelled' : 'failed', error: error.name === 'AbortError' ? 'Stopped by reviewer.' : error.message || 'Verification failed.', result: null };
        outcomes[index] = update;
        onUpdate(index, update);
      }
    }
  }
  await Promise.all(Array.from({ length: Math.min(concurrency, items.length) }, worker));
  for (let i = 0; i < items.length; i++) {
    if (!outcomes[i]) {
      outcomes[i] = { state: 'cancelled', error: 'Not started; queue stopped.', result: null };
      onUpdate(i, outcomes[i]);
    }
  }
  return outcomes;
}
