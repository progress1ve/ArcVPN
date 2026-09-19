/**
 * Утилита для логирования только в development режиме
 * В production логи не выводятся (кроме error)
 */

const isDev = import.meta.env.DEV;

type LogLevel = 'log' | 'warn' | 'debug';

function devOnly(level: LogLevel, prefix?: string) {
  return (...args: unknown[]): void => {
    if (isDev) {
      if (prefix) {
        console[level](`[${prefix}]`, ...args);
      } else {
        console[level](...args);
      }
    }
  };
}

function errorLog(prefix?: string) {
  return (...args: unknown[]): void => {
    if (prefix) {
      console.error(`[${prefix}]`, ...args);
    } else {
      console.error(...args);
    }
  };
}

function createLoggerInstance(prefix?: string) {
  return {
    log: devOnly('log', prefix),
    warn: devOnly('warn', prefix),
    error: errorLog(prefix),
    debug: devOnly('debug', prefix),
  };
}

export const logger = {
  ...createLoggerInstance(),
  createLogger: (prefix: string) => createLoggerInstance(prefix),
};

export default logger;
