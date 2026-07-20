export interface Logger {
  log(message: string, ...args: unknown[]): void;
  warn(message: string, ...args: unknown[]): void;
  error(message: string, ...args: unknown[]): void;
}

export type TimerHandle = unknown;

export interface TimerProvider {
  setInterval(callback: () => void, ms: number): TimerHandle;
  clearInterval(handle: TimerHandle): void;
}

export interface PlatformAdapter {
  logger: Logger;
  timer: TimerProvider;
}

export const noopLogger: Logger = {
  log: () => {},
  warn: () => {},
  error: () => {}
};

export const noopTimer: TimerProvider = {
  setInterval: () => null,
  clearInterval: () => {}
};
