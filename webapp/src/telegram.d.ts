interface TelegramWebApp {
  initData: string;
  initDataUnsafe: Record<string, unknown>;
  ready: () => void;
  expand: () => void;
  close: () => void;
  colorScheme: 'light' | 'dark';
  themeParams: Record<string, string>;
}

interface Window {
  Telegram?: {
    WebApp?: TelegramWebApp;
  };
}
