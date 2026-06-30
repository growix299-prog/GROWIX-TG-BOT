import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Elite Security Agency - Command Center',
  description: 'Digital Delivery System Operations Dashboard',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="antialiased selection:bg-yellow-500 selection:text-black">
        {children}
      </body>
    </html>
  )
}
