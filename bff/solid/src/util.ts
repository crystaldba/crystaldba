export function awaitTimeout(delay: number) {
  return new Promise((resolve) => setTimeout(resolve, delay));
}

export async function sleep(ms: number) {
  await new Promise((r) => setTimeout(r, ms));
}

export function truncateString(str: string, maxLength = 100) {
  if (str.length > maxLength) {
    return `${str.substring(0, maxLength - 3)}...`;
  }
  return str;
}

export function unique<T>(list: T[]): T[] {
  return [...new Set(list)];
}
