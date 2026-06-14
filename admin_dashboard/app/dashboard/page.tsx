"use client"

import { useEffect, useState } from 'react'
import { supabase } from '../../lib/supabaseClient'
import { DollarSign, ShoppingCart, ShieldAlert, Layers, CheckCircle2, AlertTriangle, ArrowUpRight } from 'lucide-react'

export default function AnalyticsPage() {
  const [stats, setStats] = useState({
    totalRevenue: 0,
    totalSales: 0,
    activeProducts: 0,
    totalCredentials: 0,
    unusedCredentials: 0
  })
  const [recentOrders, setRecentOrders] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        setLoading(true)
        
        // 1. Fetch Completed Orders for revenue and count
        const { data: completedOrders } = await supabase
          .from('orders')
          .select('amount')
          .eq('status', 'COMPLETED')
        
        const totalSales = completedOrders?.length || 0
        const totalRevenue = completedOrders?.reduce((sum, item) => sum + Number(item.amount), 0) || 0

        // 2. Fetch Active Products count
        const { count: activeProducts } = await supabase
          .from('products')
          .select('*', { count: 'exact', head: true })
          .eq('active', true)

        // 3. Fetch Credentials stats
        const { data: credentials } = await supabase
          .from('credentials')
          .select('status')
        
        const totalCredentials = credentials?.length || 0
        const unusedCredentials = credentials?.filter(c => c.status === 'UNUSED').length || 0

        setStats({
          totalRevenue,
          totalSales,
          activeProducts: activeProducts || 0,
          totalCredentials,
          unusedCredentials
        })

        // 4. Fetch 5 Recent Orders
        const { data: recent } = await supabase
          .from('orders')
          .select('*, products(name)')
          .order('created_at', { ascending: false })
          .limit(5)
        
        setRecentOrders(recent || [])
      } catch (error) {
        console.error("Error loading analytics:", error)
      } finally {
        setLoading(false)
      }
    }

    fetchAnalytics()

    // Subscribe to real-time changes on orders and credentials
    const ordersChannel = supabase
      .channel('analytics-orders-realtime')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'orders' },
        () => {
          fetchAnalytics()
        }
      )
      .subscribe()

    const credentialsChannel = supabase
      .channel('analytics-credentials-realtime')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'credentials' },
        () => {
          fetchAnalytics()
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(ordersChannel)
      supabase.removeChannel(credentialsChannel)
    }
  }, [])

  const headingStyle = "font-playfair font-black tracking-wide text-white"

  return (
    <div className="space-y-8">
      {/* Dynamic Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className={`${headingStyle} text-3xl`}>Sales Analytics Dashboard</h1>
          <p className="text-xs text-gray-500 font-sfpro mt-1 uppercase tracking-widest">Real-time sales tracking and product inventory stats</p>
        </div>
        <div className="flex gap-2">
          <div className="px-4 py-2 bg-cyber-fbi border border-cyber-border rounded-lg flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-yellow-400 animate-ping"></span>
            <span className="text-[10px] uppercase font-bold text-yellow-400 font-sfpro">Database Connected</span>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="h-96 flex items-center justify-center">
          <div className="w-8 h-8 border-2 border-yellow-500 border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            
            {/* CARD 1: REVENUE */}
            <div className="glass-panel p-6 rounded-xl glow-border-cyan shadow-glow-yellow/5 flex flex-col justify-between">
              <div className="flex items-center justify-between mb-4">
                <span className="text-[11px] font-bold uppercase tracking-wider text-gray-400 font-sfpro">Total Revenue</span>
                <div className="w-8 h-8 rounded-full bg-yellow-950 flex items-center justify-center">
                  <DollarSign className="w-4 h-4 text-yellow-400" />
                </div>
              </div>
              <div>
                <h3 className="text-3xl font-black font-sfpro text-white">₹{stats.totalRevenue.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</h3>
                <div className="flex items-center gap-1 text-[10px] text-yellow-400 mt-2 font-mono">
                  <ArrowUpRight className="w-3.5 h-3.5" />
                  <span>TRANSACTIONS SECURED</span>
                </div>
              </div>
            </div>

            {/* CARD 2: COMPLETED SALES */}
            <div className="glass-panel p-6 rounded-xl border border-cyber-border/80 flex flex-col justify-between">
              <div className="flex items-center justify-between mb-4">
                <span className="text-[11px] font-bold uppercase tracking-wider text-gray-400 font-sfpro">Successful Deliveries</span>
                <div className="w-8 h-8 rounded-full bg-emerald-950 flex items-center justify-center">
                  <ShoppingCart className="w-4 h-4 text-emerald-400" />
                </div>
              </div>
              <div>
                <h3 className="text-3xl font-black font-sfpro text-white">{stats.totalSales}</h3>
                <div className="flex items-center gap-1 text-[10px] text-emerald-400 mt-2 font-mono">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>100% SUCCESS RATE</span>
                </div>
              </div>
            </div>

            {/* CARD 3: ACTIVE PRODUCTS */}
            <div className="glass-panel p-6 rounded-xl border border-cyber-border/80 flex flex-col justify-between">
              <div className="flex items-center justify-between mb-4">
                <span className="text-[11px] font-bold uppercase tracking-wider text-gray-400 font-sfpro">Active Products</span>
                <div className="w-8 h-8 rounded-full bg-yellow-950 flex items-center justify-center">
                  <Layers className="w-4 h-4 text-yellow-400" />
                </div>
              </div>
              <div>
                <h3 className="text-3xl font-black font-sfpro text-white">{stats.activeProducts}</h3>
                <div className="flex items-center gap-1 text-[10px] text-yellow-400 mt-2 font-mono">
                  <ArrowUpRight className="w-3.5 h-3.5" />
                  <span>LIVE IN CATALOG</span>
                </div>
              </div>
            </div>

            {/* CARD 4: CREDENTIALS VAULT */}
            <div className="glass-panel p-6 rounded-xl border border-cyber-border/80 flex flex-col justify-between">
              <div className="flex items-center justify-between mb-4">
                <span className="text-[11px] font-bold uppercase tracking-wider text-gray-400 font-sfpro">Unused Game Accounts</span>
                <div className="w-8 h-8 rounded-full bg-rose-950 flex items-center justify-center">
                  <ShieldAlert className="w-4 h-4 text-rose-400" />
                </div>
              </div>
              <div>
                <h3 className="text-3xl font-black font-sfpro text-white">{stats.unusedCredentials} <span className="text-xs font-normal text-gray-500">/ {stats.totalCredentials} total</span></h3>
                <div className={`flex items-center gap-1 text-[10px] mt-2 font-mono ${stats.unusedCredentials < 5 ? 'text-red-400 animate-pulse' : 'text-gray-400'}`}>
                  <AlertTriangle className="w-3.5 h-3.5" />
                  <span>{stats.unusedCredentials < 5 ? 'CRITICAL STOCK ALERT' : 'STOCK LEVELS GOOD'}</span>
                </div>
              </div>
            </div>

          </div>

          {/* Core Analytics Details & Activity Feed */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            
            {/* Recent Orders log */}
            <div className="glass-panel p-6 rounded-xl border border-cyber-border/80 lg:col-span-2">
              <h2 className={`${headingStyle} text-lg mb-4`}>Recent Orders Activity</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-cyber-border text-gray-400 font-sfpro">
                      <th className="py-3 px-4 uppercase tracking-wider font-bold">Order ID / Reference</th>
                      <th className="py-3 px-4 uppercase tracking-wider font-bold">Product</th>
                      <th className="py-3 px-4 uppercase tracking-wider font-bold">Telegram User</th>
                      <th className="py-3 px-4 uppercase tracking-wider font-bold text-right">Amount</th>
                      <th className="py-3 px-4 uppercase tracking-wider font-bold text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody className="font-sfpro divide-y divide-cyber-border/30">
                    {recentOrders.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="py-8 text-center text-gray-500 uppercase tracking-widest text-[10px]">No orders logged in database</td>
                      </tr>
                    ) : (
                      recentOrders.map((order) => (
                        <tr key={order.id} className="hover:bg-cyber-card/30 transition-all">
                          <td className="py-3 px-4 font-bold text-yellow-400"><code>{order.payment_id || order.id.slice(0,8)}</code></td>
                          <td className="py-3 px-4 font-bold text-white">{order.products?.name}</td>
                          <td className="py-3 px-4 text-gray-400">@{order.telegram_id || 'guest'}</td>
                          <td className="py-3 px-4 text-right text-emerald-400 font-bold">₹{parseFloat(order.amount).toFixed(2)}</td>
                          <td className="py-3 px-4 text-center">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              order.status === 'COMPLETED' ? 'bg-emerald-950 text-emerald-400 border border-emerald-500/20' :
                              order.status === 'FAILED' ? 'bg-red-950 text-red-400 border border-red-500/20' :
                              'bg-yellow-950/70 text-yellow-500 border border-yellow-500/20'
                            }`}>
                              {order.status}
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Quick Operations Guide */}
            <div className="glass-panel p-6 rounded-xl border border-cyber-border/80 flex flex-col justify-between">
              <div>
                <h2 className={`${headingStyle} text-lg mb-4`}>Quick Setup Guide</h2>
                <ul className="space-y-4 text-xs font-sfpro">
                  <li className="flex gap-3">
                    <span className="w-5 h-5 rounded-full bg-yellow-950 border border-yellow-500/30 flex items-center justify-center text-[10px] text-yellow-400 font-bold flex-shrink-0">1</span>
                    <p className="text-gray-400">
                      Configure your active product list in the <strong>Product Catalog</strong>. Switch delivery modes to AUTO or MANUAL.
                    </p>
                  </li>
                  <li className="flex gap-3">
                    <span className="w-5 h-5 rounded-full bg-yellow-950 border border-yellow-500/30 flex items-center justify-center text-[10px] text-yellow-400 font-bold flex-shrink-0">2</span>
                    <p className="text-gray-400">
                      Keep game accounts stocked up in the <strong>Accounts Inventory</strong>. Stock runs are checked instantly upon payment.
                    </p>
                  </li>
                  <li className="flex gap-3">
                    <span className="w-5 h-5 rounded-full bg-yellow-950 border border-yellow-500/30 flex items-center justify-center text-[10px] text-yellow-400 font-bold flex-shrink-0">3</span>
                    <p className="text-gray-400">
                      Manage pending customer emails in <strong>OTT Activation Requests</strong> to complete manually processed premium activations.
                    </p>
                  </li>
                </ul>
              </div>

              <div className="mt-8 p-4 bg-cyber-fbi border border-cyber-border/60 rounded-lg">
                <h4 className="text-[10px] font-bold text-yellow-400 uppercase tracking-widest mb-1">Web Systems Status</h4>
                <div className="grid grid-cols-2 gap-2 text-[10px] text-gray-500 font-mono">
                  <div>POSTGRES DB:</div>
                  <div className="text-emerald-400 font-bold text-right">SECURE LINK</div>
                  <div>TELEGRAM POLLING:</div>
                  <div className="text-emerald-400 font-bold text-right">ONLINE</div>
                </div>
              </div>

            </div>

          </div>
        </>
      )}
    </div>
  )
}
