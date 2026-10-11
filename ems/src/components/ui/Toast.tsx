import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from 'react';
import checkIcon from '@/assets/icons/check.svg';
import alertIcon from '@/assets/icons/alert.svg';

type ToastTone = 'success' | 'error' | 'info';

interface ToastItem {
  id: number;
  message: string;
  tone: ToastTone;
}

interface ToastApi {
  notify: (message: string, tone?: ToastTone) => void;
}

const ToastContext = createContext<ToastApi>({ notify: () => undefined });

export function useToast(): ToastApi {
  return useContext(ToastContext);
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const nextId = useRef(1);

  const notify = useCallback((message: string, tone: ToastTone = 'success') => {
    const id = nextId.current++;
    setItems((prev) => [...prev.slice(-2), { id, message, tone }]);
    window.setTimeout(() => {
      setItems((prev) => prev.filter((item) => item.id !== id));
    }, 4200);
  }, []);

  const api = useMemo(() => ({ notify }), [notify]);

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div
        aria-live="polite"
        className="pointer-events-none fixed inset-x-0 bottom-4 z-[60] flex flex-col items-center gap-2 px-4"
      >
        {items.map((item) => (
          <p
            key={item.id}
            role="status"
            className="pointer-events-auto flex max-w-full items-center gap-2.5 rounded-xl bg-ink px-4 py-3 text-sm font-medium text-white shadow-pop"
            style={{ animation: 'ems-toast-in 180ms ease-out' }}
          >
            <img
              src={item.tone === 'error' ? alertIcon : checkIcon}
              alt=""
              aria-hidden="true"
              className="size-5 shrink-0"
            />
            <span className="break-words">{item.message}</span>
          </p>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
