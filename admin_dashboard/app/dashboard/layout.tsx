"use client"

import { useEffect, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import { supabase } from '../../lib/supabaseClient'
import { 
  Store, 
  BarChart3, 
  ShoppingBag, 
  KeyRound, 
  Receipt, 
  Mail, 
  Database, 
  LogOut,
  User,
  Activity,
  MessageSquareHeart,
  Wallet,
  Megaphone
} from 'lucide-react'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const router = useRouter()
  const pathname = usePathname()
  const [authorized, setAuthorized] = useState(false)
  const [loading, setLoading] = useState(true)
  const [adminName, setAdminName] = useState('Agent')

  useEffect(() => {
    const checkAuth = async () => {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) {
        router.push('/')
      } else {
        setAdminName(session.user.email?.split('@')[0] || 'Admin')
        setAuthorized(true)
      }
      setLoading(false)
    }

    checkAuth()
  }, [router])

  const handleLogout = async () => {
    await supabase.auth.signOut()
    router.push('/')
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-cyber-bg flex flex-col items-center justify-center">
        <div className="w-10 h-10 border-4 border-yellow-500 border-t-transparent rounded-full animate-spin mb-4"></div>
        <p className="text-xs uppercase tracking-widest text-yellow-400 font-sfpro">Decrypting Secure Connection...</p>
      </div>
    )
  }

  if (!authorized) return null

  const navigation = [
    { name: 'Sales Analytics', href: '/dashboard', icon: BarChart3 },
    { name: 'Product Catalog', href: '/dashboard/products', icon: ShoppingBag },
    { name: 'Accounts Inventory', href: '/dashboard/credentials', icon: KeyRound },
    { name: 'Purchased Orders', href: '/dashboard/orders', icon: Receipt },
    { name: 'Payment Details', href: '/dashboard/payments', icon: Database },
    { name: 'Users & Wallets', href: '/dashboard/users', icon: Wallet },
    { name: 'Customer Reviews', href: '/dashboard/reviews', icon: MessageSquareHeart },
    { name: 'Stock Broadcast', href: '/dashboard/broadcast', icon: Megaphone },
  ]

  return (
    <div className="min-h-screen bg-cyber-bg text-cyber-text flex font-poppins">
      {/* Background cyber grid */}
      <div className="fixed inset-0 bg-[linear-gradient(to_right,#0c0e12_1px,transparent_1px),linear-gradient(to_bottom,#0c0e12_1px,transparent_1px)] bg-[size:4rem_4rem] opacity-20 pointer-events-none"></div>

      {/* Sidebar Navigation */}
      <aside className="w-64 bg-cyber-fbi/80 backdrop-blur-md border-r border-cyber-border z-30 flex flex-col justify-between fixed top-0 bottom-0">
        <div className="flex-1 overflow-y-auto">
          {/* Header Panel */}
          <div className="p-6 border-b border-cyber-border flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-yellow-950 border border-yellow-500/40 flex items-center justify-center shadow-glow-yellow">
              <Store className="w-5 h-5 text-yellow-400" />
            </div>
            <div>
              <h2 className="text-[10px] font-bold text-yellow-400 uppercase tracking-widest font-sfpro">NEXUS STORE</h2>
              <h1 className="text-sm font-black font-playfair tracking-wide text-white">ADMIN CONTROL</h1>
            </div>
          </div>

          {/* Current User clearance */}
          <div className="mx-4 my-6 p-3 bg-cyber-bg/70 border border-cyber-border/40 rounded-lg flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-yellow-950 flex items-center justify-center">
              <User className="w-4 h-4 text-yellow-500" />
            </div>
            <div className="overflow-hidden">
              <p className="text-[10px] text-gray-500 font-bold uppercase tracking-wider font-sfpro">Access Verified</p>
              <p className="text-xs text-cyber-text truncate font-bold font-sfpro">{adminName}</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="px-4 space-y-1 pb-6">
            {navigation.map((item) => {
              const isActive = pathname === item.href
              const Icon = item.icon
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-xs font-medium cursor-pointer transition-all group font-sfpro ${
                    isActive
                      ? 'bg-yellow-950/50 border border-yellow-500/30 text-yellow-400 shadow-glow-yellow'
                      : 'text-gray-400 hover:text-white hover:bg-cyber-card/60 border border-transparent'
                  }`}
                >
                  <Icon className={`w-4.5 h-4.5 transition-all ${isActive ? 'text-yellow-400' : 'text-gray-500 group-hover:text-yellow-400'}`} />
                  <span>{item.name}</span>
                </Link>
              )
            })}
          </nav>
        </div>

        {/* Bottom Footer Actions */}
        <div className="p-4 border-t border-cyber-border/40 space-y-3">
          <div className="flex items-center justify-between text-[10px] text-yellow-500/60 font-mono px-2">
            <div className="flex items-center gap-1">
              <Activity className="w-3 h-3 text-yellow-400 animate-pulse" />
              <span>SERVER: LIVE</span>
            </div>
            <span>V2.4.9</span>
          </div>

          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-red-950/20 hover:bg-red-950/40 border border-red-500/20 hover:border-red-500/40 text-red-400 rounded-lg text-xs font-bold uppercase tracking-widest cursor-pointer transition-all font-sfpro shadow-glow-red/5"
          >
            <LogOut className="w-4 h-4" />
            <span>Logout</span>
          </button>
        </div>
      </aside>

      {/* Main dashboard content area */}
      <div className="flex-1 pl-64 relative z-10 flex flex-col min-h-screen">
        <header className="h-16 border-b border-cyber-border/50 bg-cyber-bg/50 backdrop-blur-md sticky top-0 px-8 flex items-center justify-between z-20">
          <h2 className="text-xs uppercase tracking-[0.2em] text-yellow-400/80 font-bold font-sfpro">Nexus Admin Console</h2>
          <div className="flex items-center gap-4 text-xs">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-ping"></span>
            <span className="text-gray-500 font-sfpro">Database Status: Connected</span>
          </div>
        </header>
        <main className="flex-1 p-8 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  )
}
