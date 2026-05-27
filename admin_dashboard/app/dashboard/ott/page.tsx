"use client"

import { useEffect, useState } from 'react'
import { supabase } from '../../../lib/supabaseClient'
import { Mail, CheckCircle2, User, RefreshCw, AlertCircle, Trash2, XCircle, Filter } from 'lucide-react'

export default function OttRequestsPage() {
  const [requests, setRequests] = useState<any[]>([])
  const [filteredRequests, setFilteredRequests] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [actioningId, setActioningId] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState('ALL')

  const fetchRequests = async () => {
    try {
      setLoading(true)
      const { data, error } = await supabase
        .from('ott_requests')
        .select('*, orders(*, products(*))')
        .order('created_at', { ascending: false })
      if (error) throw error
      setRequests(data || [])
    } catch (err: any) {
      console.error(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchRequests()
  }, [])

  // Filter logic
  useEffect(() => {
    if (statusFilter === 'ALL') {
      setFilteredRequests(requests)
    } else {
      setFilteredRequests(requests.filter(r => r.status === statusFilter))
    }
  }, [statusFilter, requests])

  const handleActivate = async (req: any) => {
    
    setActioningId(req.id)
    try {
      const productId = req.orders?.products?.id;
      if (!productId) throw new Error("Product ID missing");

      // 1. Fetch unused credential from Accounts Inventory
      const { data: creds, error: fetchError } = await supabase
        .from('credentials')
        .select('*')
        .eq('product_id', productId)
        .eq('status', 'UNUSED')
        .limit(1);

      if (fetchError) throw fetchError;
      if (!creds || creds.length === 0) {
        throw new Error(`No stock available for ${req.orders?.products?.name}! Please add credentials to the Inventory first.`);
      }

      const credential = creds[0];

      // 2. Mark credential as USED
      const { error: updateError } = await supabase
        .from('credentials')
        .update({ status: 'USED' })
        .eq('id', credential.id);

      if (updateError) throw updateError;

      // 3. Send Credentials via backend (Resend + Telegram Notification)
      const backendBaseUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "https://nexautomate-backend.onrender.com";
      const backendUrl = `${backendBaseUrl}/api/admin/send-ott-credentials`;
      const payload = {
        order_id: req.order_id,
        product_name: req.orders?.products?.name || 'OTT Subscription',
        customer_email: req.customer_email,
        telegram_id: req.orders?.telegram_id,
        username: credential.email_or_username,
        password: credential.password
      };
      
      const response = await fetch(backendUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-API-Key": process.env.NEXT_PUBLIC_ADMIN_API_SECRET || ""
        },
        body: JSON.stringify(payload)
      });
      
      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || "Failed to send credential email");
      }

      // 2. Update OTT Request Status
      const { error: reqError } = await supabase
        .from('ott_requests')
        .update({ status: 'COMPLETED' })
        .eq('id', req.id)
      if (reqError) throw reqError

      // 3. Update Order Delivery Status
      const { error: orderError } = await supabase
        .from('orders')
        .update({ delivery_status: 'DELIVERED' })
        .eq('id', req.order_id)
      if (orderError) throw orderError

      fetchRequests()
    } catch (err: any) {
      alert("Activation failed: " + err.message)
    } finally {
      setActioningId(null)
    }
  }

  const handleCancelActivation = async (req: any) => {
    if (!confirm(`Cancel activation for "${req.orders?.products?.name}"? This will revert the order to PENDING status. The user will NOT be notified.`)) return
    
    setActioningId(req.id)
    try {
      // 1. Revert OTT Request Status to PENDING
      const { error: reqError } = await supabase
        .from('ott_requests')
        .update({ status: 'PENDING' })
        .eq('id', req.id)
      if (reqError) throw reqError

      // 2. Revert Order Delivery Status
      const { error: orderError } = await supabase
        .from('orders')
        .update({ delivery_status: 'MANUAL_PROCESSING' })
        .eq('id', req.order_id)
      if (orderError) throw orderError

      fetchRequests()
    } catch (err: any) {
      alert("Cancel failed: " + err.message)
    } finally {
      setActioningId(null)
    }
  }

  const handleDeleteRequest = async (req: any) => {
    if (!confirm(`⚠️ PERMANENTLY DELETE this OTT request for "${req.orders?.products?.name}"?\n\nThis will also delete the associated order and payment records from the database. This action CANNOT be undone.`)) return
    
    setActioningId(req.id)
    try {
      const orderId = req.order_id
      const paymentId = req.orders?.payment_id

      // 1. Delete OTT Request first (child)
      const { error: ottError } = await supabase
        .from('ott_requests')
        .delete()
        .eq('id', req.id)
      if (ottError) throw ottError

      // 2. Delete associated payment record if exists
      if (paymentId) {
        await supabase.from('payments').delete().eq('razorpay_payment_id', paymentId)
        await supabase.from('payments').delete().eq('razorpay_order_id', paymentId)
      }

      // 3. Delete the order itself
      if (orderId) {
        const { error: orderError } = await supabase
          .from('orders')
          .delete()
          .eq('id', orderId)
        if (orderError) console.error("Could not delete order:", orderError.message)
      }

      fetchRequests()
    } catch (err: any) {
      alert("Delete failed: " + err.message)
    } finally {
      setActioningId(null)
    }
  }

  const pendingCount = requests.filter(r => r.status === 'PENDING').length
  const completedCount = requests.filter(r => r.status === 'COMPLETED').length
  const headingStyle = "font-playfair font-black tracking-wide text-white"

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className={`${headingStyle} text-3xl`}>OTT Activation Center</h1>
          <p className="text-xs text-gray-500 font-sfpro mt-1 uppercase tracking-widest font-bold">Manage streaming subscription activation requests</p>
        </div>
        <button
          onClick={fetchRequests}
          className="p-2.5 bg-cyber-fbi border border-cyber-border hover:border-yellow-500/40 rounded-lg text-gray-400 hover:text-yellow-400 transition-all"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Status Filter Tabs */}
      <div className="flex items-center gap-3 text-xs font-sfpro">
        <Filter className="w-4 h-4 text-gray-500" />
        {[
          { key: 'ALL', label: `All (${requests.length})` },
          { key: 'PENDING', label: `Pending (${pendingCount})`, color: 'purple' },
          { key: 'COMPLETED', label: `Completed (${completedCount})`, color: 'emerald' },
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setStatusFilter(tab.key)}
            className={`px-3 py-1.5 rounded-lg font-bold uppercase tracking-wider text-[10px] transition-all border ${
              statusFilter === tab.key
                ? 'bg-yellow-950/60 text-yellow-400 border-yellow-500/30'
                : 'bg-cyber-card text-gray-500 border-cyber-border hover:text-gray-300'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="h-96 flex items-center justify-center">
          <div className="w-8 h-8 border-2 border-yellow-500 border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {filteredRequests.length === 0 ? (
            <div className="col-span-full glass-panel py-16 text-center text-gray-500 uppercase tracking-widest text-xs font-sfpro border border-cyber-border rounded-xl">
              <Mail className="w-12 h-12 mx-auto mb-4 text-gray-600 animate-pulse" />
              <span>No OTT activation tickets found</span>
            </div>
          ) : (
            filteredRequests.map((req) => {
              const isCompleted = req.status === 'COMPLETED'
              const isActioning = actioningId === req.id
              return (
                <div 
                  key={req.id} 
                  className={`glass-panel p-6 rounded-xl border relative transition-all overflow-hidden flex flex-col justify-between ${
                    isCompleted ? 'border-cyber-border/40 opacity-70' : 'border-purple-500/30 shadow-glow-yellow/5 hover:border-purple-500/60'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-4">
                      <span className={`px-2.5 py-0.5 rounded text-[9px] font-black tracking-widest uppercase font-sfpro ${
                        isCompleted ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-500/20' : 'bg-purple-950 text-purple-400 border border-purple-500/30 animate-pulse'
                      }`}>
                        {req.status}
                      </span>
                      <span className="text-[10px] text-gray-500 font-mono">
                        {req.created_at?.slice(0, 19).replace('T', ' ')}
                      </span>
                    </div>

                    <h3 className="text-base font-bold text-white tracking-wide truncate mb-1">
                      {req.orders?.products?.name || 'OTT Subscription'}
                    </h3>
                    
                    <div className="text-xs font-sfpro space-y-1.5 mt-3">
                      <div className="flex items-center gap-2 text-yellow-400 font-bold">
                        <Mail className="w-4 h-4 text-yellow-500/50" />
                        <span>Email: <code className="select-all font-mono font-normal text-white">{req.customer_email}</code></span>
                      </div>
                      <div className="flex items-center gap-2 text-gray-400">
                        <User className="w-4 h-4 text-gray-500" />
                        <span>Client TG: <code className="font-bold text-gray-300">@{req.orders?.telegram_id}</code></span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-4 border-t border-cyber-border/30 mt-4">
                    <div className="text-[10px] text-gray-500 font-mono">
                      Ref: <code>{req.order_id?.slice(0, 8)}</code>
                    </div>

                    <div className="flex items-center gap-2">
                      {/* Cancel Activation (revert to PENDING) - only for COMPLETED */}
                      {isCompleted && (
                        <button
                          onClick={() => handleCancelActivation(req)}
                          disabled={isActioning}
                          className="flex items-center gap-1 px-3 py-1.5 bg-orange-950/40 hover:bg-orange-950/60 text-orange-400 border border-orange-500/20 rounded-lg text-[10px] font-bold uppercase tracking-wider transition-all disabled:opacity-50"
                          title="Revert activation back to PENDING"
                        >
                          <XCircle className="w-3.5 h-3.5" />
                          <span>Revert</span>
                        </button>
                      )}

                      {/* Mark Activated - only for PENDING */}
                      {!isCompleted && (
                        <button
                          onClick={() => handleActivate(req)}
                          disabled={isActioning}
                          className="flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-bold rounded-lg text-[10px] tracking-wider uppercase font-sfpro transition-all shadow-glow-yellow active:scale-[0.98] disabled:opacity-50"
                        >
                          {isActioning ? (
                            <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                          ) : (
                            <>
                              <CheckCircle2 className="w-3.5 h-3.5" />
                              <span>Activate</span>
                            </>
                          )}
                        </button>
                      )}

                      {/* Delete - always available */}
                      <button
                        onClick={() => handleDeleteRequest(req)}
                        disabled={isActioning}
                        className="p-1.5 bg-red-950/30 border border-red-500/30 text-red-400 rounded-lg hover:bg-red-900/50 hover:text-red-300 transition-colors disabled:opacity-50"
                        title="Permanently delete this request + order"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              )
            })
          )}
        </div>
      )}
    </div>
  )
}
