import type { Metadata } from 'next'
import { Poppins, Open_Sans } from 'next/font/google'
import './globals.css'
import QueryProvider from '@/lib/QueryProvider'
import Navigation from '@/components/Navigation'
import { App } from 'antd'

const poppins = Poppins({
  weight: ['400', '500', '600', '700'],
  subsets: ['latin'],
  variable: '--font-heading',
})

const openSans = Open_Sans({
  weight: ['300', '400', '500', '600', '700'],
  subsets: ['latin'],
  variable: '--font-body',
})

export const metadata: Metadata = {
  title: 'Quantitative Trading Platform',
  description: 'Personal quantitative trading platform for backtesting and strategy optimization',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={`${poppins.variable} ${openSans.variable}`}>
      <body className={`${openSans.className} font-body antialiased`}>
        <App>
          <QueryProvider>
            <Navigation />
            <main className="min-h-screen bg-slate-50 dark:bg-slate-900 pt-14">
              {children}
            </main>
          </QueryProvider>
        </App>
      </body>
    </html>
  )
}
