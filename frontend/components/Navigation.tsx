'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LineChart, Database, Play, Settings2, TrendingUp, Moon, Sun, Clock, Activity } from 'lucide-react';

export default function Navigation() {
  const pathname = usePathname();
  const [darkMode, setDarkMode] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    // Check for saved preference or system preference
    const savedTheme = localStorage.getItem('theme');
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    if (savedTheme === 'dark' || (!savedTheme && systemPrefersDark)) {
      setDarkMode(true);
      document.documentElement.classList.add('dark');
    }
  }, []);

  const toggleDarkMode = () => {
    setDarkMode(!darkMode);
    if (!darkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  };

  const navLinks = [
    { href: '/strategies', label: 'Strategies', icon: TrendingUp },
    { href: '/data', label: 'Data', icon: Database },
    { href: '/backtest', label: 'Backtest', icon: Play },
    { href: '/optimize', label: 'Optimize', icon: Settings2 },
    { href: '/history', label: 'History', icon: Clock },
    { href: '/live', label: 'Live', icon: Activity },
  ];

  const isActive = (href: string) => pathname === href;

  return (
    <nav className="bg-white/80 dark:bg-slate-800/80 backdrop-blur-md shadow-sm border-b border-slate-200 dark:border-slate-700 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-14">
          <div className="flex items-center">
            <Link href="/" className="flex items-center gap-2 group cursor-pointer">
              <LineChart className="h-7 w-7 text-primary-600 group-hover:text-primary-700 transition-colors" />
              <span className="text-lg font-heading font-bold text-slate-900 dark:text-slate-100 group-hover:text-slate-800 dark:group-hover:text-slate-200 transition-colors">
                Quant Platform
              </span>
            </Link>
          </div>

          <div className="flex items-center space-x-1">
            {navLinks.map(({ href, label, icon: Icon }) => {
              const active = isActive(href);
              return (
                <Link
                  key={href}
                  href={href}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all duration-200 cursor-pointer ${
                    active
                      ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-400 border-b-2 border-primary-600'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-50 dark:hover:bg-slate-700/50'
                  }`}
                  aria-current={active ? 'page' : undefined}
                >
                  <Icon className="h-4 w-4" />
                  <span className="hidden sm:inline">{label}</span>
                </Link>
              );
            })}

            {mounted && (
              <button
                onClick={toggleDarkMode}
                className="ml-2 p-2 rounded-lg text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-all duration-200 cursor-pointer"
                aria-label={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
              >
                {darkMode ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
              </button>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
