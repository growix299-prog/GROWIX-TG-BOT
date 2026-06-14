"use client"

import { useEffect, useState } from 'react'
import { supabase } from '../../../lib/supabaseClient'
import { Search, Filter, Receipt, RefreshCw, Trash2 } from 'lucide-react'

export default function OrdersPage() {
  const [orders, setOrders] = useState<any[]>([])
  const [filteredOrders, setFilteredOrders] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  
  // Search / Filters
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [deliveryFilter, setDeliveryFilter] = useState('ALL')

  const fetchOrders = async () => {
    try {
      setLoading(true)
      const { data, error } = await supabase
        .from('orders')
        .select('*, products(name, category)')
        .order('created_at', { ascending: false })
      if (error) throw error
      setOrders(data || [])
      setFilteredOrders(data || [])
    } catch (err: any) {
      console.error(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchOrders()
  }, [])

  const handleDeleteOrder = async (orderId: string, paymentId: string | null) => {
    if (!window.confirm("Are you sure you want to permanently delete this order and its payment details?")) return;
    try {
      if (paymentId) {
        await supabase.from('payments').delete().eq('payment_id', paymentId);
      }
      const { error } = await supabase.from('orders').delete().eq('id', orderId);
      if (error) throw error;
      fetchOrders();
    } catch (err: any) {
      alert("Failed to delete order: " + err.message);
    }
  }

  useEffect(() => {
    let result = orders

    if (search.trim()) {
      const q = search.toLowerCase().trim()
      result = result.filter(order => 
        String(order.telegram_id).toLowerCase().includes(q) ||
        (order.payment_id && order.payment_id.toLowerCase().includes(q)) ||
        (order.products?.name && order.products.name.toLowerCase().includes(q))
      )
    }

    if (statusFilter !== 'ALL') {
      result = result.filter(order => order.status === statusFilter)
    }

    if (deliveryFilter !== 'ALL') {
      result = result.filter(order => order.delivery_status === deliveryFilter)
    }

    setFilteredOrders(result)
  }, [search, statusFilter, deliveryFilter, orders])

  const headingStyle = "font-playfair font-black tracking-wide text-white"

  return (
    <div className="space-y-8">
      {/* Dynamic Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className={`${headingStyle} text-3xl`}>Order Registry Logs</h1>
          <p className="text-xs text-gray-500 font-sfpro mt-1 uppercase tracking-widest font-bold">Search, filter, and audit digital sales invoices</p>
        </div>
        <button
          onClick={fetchOrders}
          className="p-2.5 bg-cyber-fbi border border-cyber-border hover:border-yellow-500/40 rounded-lg text-gray-400 hover:text-yellow-400 transition-all"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Filter Options */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs font-sfpro">
        
        {/* Search */}
        <div className="md:col-span-2 relative">
          <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="h-4 w-4 text-yellow-500/40" />
          </span>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by User TG ID, Payment Reference, or Product..."
            className="w-full pl-10 pr-4 py-2.5 bg-cyber-card border border-cyber-border rounded-lg text-cyber-text placeholder-gray-600 focus:outline-none focus:border-yellow-400"
          />
        </div>

        {/* Status Filter */}
        <div className="relative">
          <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Filter className="h-4 w-4 text-yellow-500/40" />
          </span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-cyber-card border border-cyber-border rounded-lg text-cyber-text focus:outline-none focus:border-yellow-400"
          >
            <option value="ALL">All Payments</option>
            <option value="PENDING">PENDING</option>
            <option value="COMPLETED">COMPLETED</option>
            <option value="FAILED">FAILED</option>
          </select>
        </div>

        {/* Delivery Filter */}
        <div className="relative">
          <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Filter className="h-4 w-4 text-yellow-500/40" />
          </span>
          <select
            value={deliveryFilter}
            onChange={(e) => setDeliveryFilter(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-cyber-card border border-cyber-border rounded-lg text-cyber-text focus:outline-none focus:border-yellow-400"
          >
            <option value="ALL">All Deliveries</option>
            <option value="PENDING">Pending</option>
            <option value="DELIVERED">Delivered</option>
            <option value="MANUAL_PROCESSING">Manual Processing</option>
            <option value="AWAITING_EMAIL_GAMES">Awaiting Email</option>
          </select>
        </div>

      </div>

      {/* Main Table */}
      {loading ? (
        <div className="h-96 flex items-center justify-center">
          <div className="w-8 h-8 border-2 border-yellow-500 border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : (
        <div className="glass-panel rounded-xl border border-cyber-border/80 shadow-glass overflow-hidden">
          <div className="max-h-[calc(100vh-260px)] overflow-y-auto overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs relative">
              <thead>
                <tr className="border-b border-cyber-border text-gray-400 font-sfpro bg-[#0a0c10] sticky top-0 z-10 shadow-sm">
                  <th className="py-2.5 px-3 uppercase tracking-wider font-bold bg-[#0a0c10]">Transaction Reference</th>
                  <th className="py-2.5 px-3 uppercase tracking-wider font-bold bg-[#0a0c10]">Date & Time</th>
                  <th className="py-2.5 px-3 uppercase tracking-wider font-bold bg-[#0a0c10]">Client TG ID</th>
                  <th className="py-2.5 px-3 uppercase tracking-wider font-bold bg-[#0a0c10]">Email</th>
                  <th className="py-2.5 px-3 uppercase tracking-wider font-bold bg-[#0a0c10]">Product Item</th>
                  <th className="py-2.5 px-3 uppercase tracking-wider font-bold bg-[#0a0c10]">Category</th>
                  <th className="py-2.5 px-3 uppercase tracking-wider font-bold text-right bg-[#0a0c10]">Price paid</th>
                  <th className="py-2.5 px-3 uppercase tracking-wider font-bold text-center bg-[#0a0c10]">Payment Status</th>
                  <th className="py-2.5 px-3 uppercase tracking-wider font-bold text-center bg-[#0a0c10]">Delivery Status</th>
                  <th className="py-2.5 px-3 uppercase tracking-wider font-bold text-center bg-[#0a0c10]">Email Sent</th>
                  <th className="py-2.5 px-3 uppercase tracking-wider font-bold text-center bg-[#0a0c10]">Actions</th>
                </tr>
              </thead>
              <tbody className="font-sfpro divide-y divide-cyber-border/30 bg-cyber-bg/40">
                {filteredOrders.length === 0 ? (
                  <tr>
                    <td colSpan={11} className="py-16 text-center text-gray-500 uppercase tracking-widest text-[10px]">
                      <Receipt className="w-12 h-12 mx-auto mb-4 text-gray-600 animate-pulse" />
                      <span>No matching transaction logs found</span>
                    </td>
                  </tr>
                ) : (
                  filteredOrders.map((order) => (
                    <tr key={order.id} className="hover:bg-cyber-card/30 transition-all font-medium border-b border-cyber-border/20">
                      <td className="py-2.5 px-3 font-bold text-yellow-400">
                        <div className="max-w-[160px] truncate select-all font-mono" title={order.payment_id || order.id}>
                          {order.payment_id || order.id.slice(0, 16)}
                        </div>
                      </td>
                      <td className="py-2.5 px-3 text-gray-400 font-medium text-[11px]">
                        <div className="w-[125px]">
                          {new Date(order.created_at).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', dateStyle: 'medium', timeStyle: 'short' })}
                        </div>
                      </td>
                      <td className="py-2.5 px-3 text-gray-400 font-bold">
                        <div className="max-w-[110px] truncate" title={`@${order.telegram_id}`}>
                          @{order.telegram_id}
                        </div>
                      </td>
                      <td className="py-2.5 px-3 text-gray-400 font-medium">
                        <div className="max-w-[130px] truncate" title={order.customer_email || 'Not Provided'}>
                          {order.customer_email || <span className="text-gray-600 text-[10px]">Not Provided</span>}
                        </div>
                      </td>
                      <td className="py-2.5 px-3 font-bold text-white">
                        <div className="max-w-[160px] truncate" title={order.products?.name}>
                          {order.products?.name}
                          {order.subscription_months > 0 && <span className="ml-1 text-gray-400 font-normal">({order.subscription_months}M)</span>}
                          {order.quantity > 1 && <span className="ml-1 text-yellow-500 text-[10px]">x{order.quantity}</span>}
                        </div>
                      </td>
                      <td className="py-2.5 px-3">
                        <span className={`px-2 py-0.5 rounded text-[9px] font-bold ${
                          order.products?.category === 'OTT' 
                            ? 'bg-purple-950/70 text-purple-400 border border-purple-500/10' 
                            : 'bg-yellow-950/70 text-yellow-400 border border-yellow-500/10'
                        }`}>
                          {order.products?.category}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right text-emerald-400 font-bold">₹{parseFloat(order.amount).toFixed(2)}</td>
                      
                      {/* Payment Badge */}
                      <td className="py-2.5 px-3 text-center">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          order.status === 'COMPLETED' ? 'bg-emerald-950 text-emerald-400 border border-emerald-500/20' :
                          order.status === 'FAILED' ? 'bg-red-950 text-red-400 border border-red-500/20' :
                          'bg-yellow-950 text-yellow-500 border border-yellow-500/20'
                        }`}>
                          {order.status}
                        </span>
                      </td>

                      {/* Delivery Badge */}
                      <td className="py-2.5 px-3 text-center font-bold">
                        <span className={`px-2 py-0.5 rounded text-[10px] ${
                          order.delivery_status === 'DELIVERED' ? 'bg-yellow-950 text-yellow-400 border border-yellow-500/20' :
                          order.delivery_status === 'MANUAL_PROCESSING' ? 'bg-purple-950 text-purple-400 border border-purple-500/20 animate-pulse' :
                          order.delivery_status === 'AWAITING_EMAIL_GAMES' ? 'bg-orange-950 text-orange-400 border border-orange-500/20 animate-pulse' :
                          'bg-yellow-950 text-yellow-500 border border-yellow-500/20'
                        }`}>
                          {order.delivery_status === 'AWAITING_EMAIL_GAMES' ? 'AWAITING EMAIL' : 
                           order.delivery_status === 'MANUAL_PROCESSING' ? 'MANUAL PROCESSING' : 
                           order.delivery_status}
                        </span>
                      </td>

                      {/* Email Status Badge */}
                      <td className="py-2.5 px-3 text-center">
                        {order.email_sent ? (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-400 border border-emerald-500/20">SENT</span>
                        ) : (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-gray-800 text-gray-400 border border-gray-600/20">NO</span>
                        )}
                      </td>

                      {/* Actions */}
                      <td className="py-2.5 px-3 text-center">
                        <button
                          onClick={() => handleDeleteOrder(order.id, order.payment_id)}
                          className="p-1.5 bg-red-950/30 border border-red-500/30 text-red-400 rounded hover:bg-red-900/50 hover:text-red-300 transition-colors"
                          title="Permanently Delete Order"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
