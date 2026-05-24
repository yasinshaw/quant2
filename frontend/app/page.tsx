import Link from 'next/link';
import { TrendingUp, Database, Play, Settings2, ArrowRight, LineChart, Activity, BarChart3, Zap } from 'lucide-react';

export default function Home() {
  const stats = [
    { label: 'Total Strategies', value: '3', icon: TrendingUp, color: 'blue' },
    { label: 'Available Symbols', value: '5', icon: Activity, color: 'green' },
    { label: 'Recent Backtests', value: '12', icon: BarChart3, color: 'purple' },
    { label: 'Recent Optimizations', value: '8', icon: Zap, color: 'orange' },
  ];

  const quickActions = [
    {
      title: 'Manage Strategies',
      description: 'View and configure your trading strategies',
      href: '/strategies',
      icon: TrendingUp,
      color: 'bg-primary-50 dark:bg-primary-900/10 hover:bg-primary-100 dark:hover:bg-primary-900/20 border-primary-200 dark:border-primary-800',
    },
    {
      title: 'Download Data',
      description: 'Fetch historical market data from Binance',
      href: '/data',
      icon: Database,
      color: 'bg-emerald-50 dark:bg-emerald-900/10 hover:bg-emerald-100 dark:hover:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800',
    },
    {
      title: 'Run Backtest',
      description: 'Test your strategies against historical data',
      href: '/backtest',
      icon: Play,
      color: 'bg-violet-50 dark:bg-violet-900/10 hover:bg-violet-100 dark:hover:bg-violet-900/20 border-violet-200 dark:border-violet-800',
    },
    {
      title: 'Optimize Parameters',
      description: 'Find optimal strategy parameters',
      href: '/optimize',
      icon: Settings2,
      color: 'bg-cta-50 dark:bg-cta-900/10 hover:bg-cta-100 dark:hover:bg-cta-900/20 border-cta-200 dark:border-cta-800',
    },
  ];

  const colorClasses: Record<string, { bg: string; text: string; icon: string }> = {
    blue: { bg: 'bg-primary-50 dark:bg-primary-900/20', text: 'text-primary-700 dark:text-primary-400', icon: 'text-primary-600 dark:text-primary-500' },
    green: { bg: 'bg-emerald-50 dark:bg-emerald-900/20', text: 'text-emerald-700 dark:text-emerald-400', icon: 'text-emerald-600 dark:text-emerald-500' },
    purple: { bg: 'bg-violet-50 dark:bg-violet-900/20', text: 'text-violet-700 dark:text-violet-400', icon: 'text-violet-600 dark:text-violet-500' },
    orange: { bg: 'bg-cta-50 dark:bg-cta-900/20', text: 'text-cta-700 dark:text-cta-400', icon: 'text-cta-600 dark:text-cta-500' },
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Hero Section */}
      <div className="mb-12">
        <div className="flex items-center gap-3 mb-4">
          <LineChart className="h-10 w-10 text-primary-600" />
          <h1 className="text-4xl font-heading font-bold text-slate-900 dark:text-slate-100">
            Quantitative Trading Platform
          </h1>
        </div>
        <p className="text-xl text-slate-600 dark:text-slate-400 max-w-3xl font-body">
          A comprehensive platform for backtesting trading strategies, optimizing parameters,
          and analyzing market data. Build, test, and refine your quantitative trading strategies
          with powerful tools and intuitive interfaces.
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
        {stats.map((stat) => {
          const colors = colorClasses[stat.color];
          return (
            <div
              key={stat.label}
              className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6 hover:shadow-lg hover:border-slate-300 dark:hover:border-slate-600 transition-all duration-200 cursor-pointer"
            >
              <div className="flex items-center justify-between mb-4">
                <div className={`p-3 rounded-lg ${colors.bg}`}>
                  <stat.icon className={`h-6 w-6 ${colors.icon}`} />
                </div>
              </div>
              <div className="text-3xl font-heading font-bold text-slate-900 dark:text-slate-100 mb-1">
                {stat.value}
              </div>
              <div className="text-sm font-medium text-slate-600 dark:text-slate-400">
                {stat.label}
              </div>
            </div>
          );
        })}
      </div>

      {/* Quick Actions */}
      <div>
        <h2 className="text-2xl font-heading font-bold text-slate-900 dark:text-slate-100 mb-6">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {quickActions.map((action) => (
            <Link
              key={action.href}
              href={action.href}
              className={`group rounded-xl border-2 p-6 transition-all duration-200 cursor-pointer ${action.color}`}
            >
              <div className="flex items-start gap-4">
                <div className="p-3 bg-white dark:bg-slate-800 rounded-lg shadow-sm">
                  <action.icon className="h-6 w-6 text-slate-700 dark:text-slate-300" />
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-heading font-semibold text-slate-900 dark:text-slate-100 mb-2 flex items-center gap-2">
                    {action.title}
                    <ArrowRight className="h-4 w-4 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </h3>
                  <p className="text-slate-600 dark:text-slate-400 font-body">{action.description}</p>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}

