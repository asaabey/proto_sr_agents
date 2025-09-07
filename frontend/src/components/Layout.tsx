import React from 'react';

export const ThemeToggle: React.FC = () => {
    const toggle = () => {
        document.documentElement.classList.toggle('dark');
        localStorage.setItem('theme', document.documentElement.classList.contains('dark') ? 'dark' : 'light');
    };
    React.useEffect(() => {
        const stored = localStorage.getItem('theme');
        if (stored === 'dark') document.documentElement.classList.add('dark');
    }, []);
    return (
        <button onClick={toggle} className="px-2 py-1 rounded border text-xs">
            Toggle Theme
        </button>
    );
};

export const Container: React.FC<React.PropsWithChildren> = ({ children }) => (
    <div className="mx-auto max-w-7xl p-4 space-y-4">{children}</div>
);

export const Card: React.FC<React.PropsWithChildren<{ title?: string; footer?: React.ReactNode }>> = ({ title, children, footer }) => (
    <div className="rounded-lg border bg-card text-card-foreground shadow-sm">
        {title && <div className="border-b px-4 py-2 font-semibold">{title}</div>}
        <div className="p-4 space-y-2">{children}</div>
        {footer && <div className="border-t px-4 py-2 text-sm text-muted-foreground">{footer}</div>}
    </div>
);
