"use client"

import { useEffect, useState } from 'react'
import { supabase } from '../../../lib/supabaseClient'
import { Database, ShieldCheck, AlertCircle, RefreshCw, Trash2 } from 'lucide-react'

export default function PaymentsPage() {
  const [payments, setPayments] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedPayload, setSelectedPayload] = useState<any | null>(null)

  const fetchPayments = async () => {
    try {
      setLoading(true)
      const { data, error } = await supabase
        .from('payments')
        .select('*')
        .order('created_at', { ascending: false })
      if (error) throw error
      setPayments(data || [])
    } catch (err: any) {
      console.error(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPayments()

    // Subscribe to real-time changes
    const channel = supabase
      .channel('payments-realtime')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'payments' },
        (payload) => {
          console.log('Payment realtime change:', payload)
          fetchPayments()
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [])

  const handleDeletePayment = async (paymentId: string) => {
    if (!window.confirm("Are you sure you want to permanently delete this payment log?")) return;
    try {
      const { error } = await supabase.from('payments').delete().eq('id', paymentId);
      if (error) throw error;
      fetchPayments();
      setSelectedPayload(null);
    } catch (err: any) {
      alert("Failed to delete payment: " + err.message);
    }
  }

  const headingStyle = "font-playfair font-black tracking-wide text-white"

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className={`${headingStyle} text-3xl`}>Payment Details</h1>
          <p className="text-xs text-gray-500 font-sfpro mt-1 uppercase tracking-widest font-bold">View and verify customer payment transactions</p>
        </div>
        <button
          onClick={fetchPayments}
          className="p-2.5 bg-cyber-fbi border border-cyber-border hover:border-yellow-500/40 rounded-lg text-gray-400 hover:text-yellow-400 transition-all"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 text-xs font-sfpro">
        
        {/* Left Column: Log */}
        <div className="glass-panel p-6 rounded-xl border border-cyber-border/80 lg:col-span-2 space-y-4">
          <h2 className={`${headingStyle} text-lg`}>Razorpay Payment Logs</h2>
          
          <div className="overflow-x-auto max-h-[500px]">
            <table className="w-full min-w-[700px] text-left border-collapse">
              <thead>
                <tr className="border-b border-cyber-border text-gray-400 sticky top-0 bg-cyber-card/90 backdrop-blur-sm z-10">
                  <th className="py-3 px-4 uppercase tracking-wider font-bold">Payment ID</th>
                  <th className="py-3.5 px-4 uppercase tracking-wider font-bold text-center">Amount</th>
                  <th className="py-3 px-4 uppercase tracking-wider font-bold text-center">Verification</th>
                  <th className="py-3 px-4 uppercase tracking-wider font-bold text-center">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-cyber-border/30">
                {payments.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="py-12 text-center text-gray-500 uppercase tracking-widest text-[10px]">
                      <Database className="w-12 h-12 mx-auto mb-4 text-gray-600 animate-pulse" />
                      <span>No transactions registered yet</span>
                    </td>
                  </tr>
                ) : (
                  payments.map((pay) => (
                    <tr key={pay.id} className="hover:bg-cyber-card/30 transition-all font-medium">
                      <td className="py-3.5 px-4 font-bold text-yellow-400">
                        <code>{pay.razorpay_payment_id || 'N/A'}</code>
                      </td>
                      <td className="py-3.5 px-4 text-center text-emerald-400 font-bold">
                        ₹{parseFloat(pay.amount || '0').toFixed(2)}
                      </td>
                      <td className="py-3.5 px-4 text-center">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[9px] font-black tracking-widest uppercase border ${
                          pay.verified 
                            ? 'bg-emerald-950/60 text-emerald-400 border-emerald-500/20 shadow-glow-green/10' 
                            : 'bg-red-950/60 text-red-400 border-red-500/20 shadow-glow-red/10'
                        }`}>
                          {pay.verified ? <ShieldCheck className="w-3 h-3 text-emerald-400" /> : <AlertCircle className="w-3 h-3 text-red-400" />}
                          <span>{pay.verified ? 'Verified' : 'Failed'}</span>
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-center">
                        <div className="flex items-center justify-center gap-2">
                          <button
                            onClick={() => setSelectedPayload(pay.payload)}
                            className="px-2.5 py-1 bg-cyber-bg hover:bg-yellow-950/30 text-gray-400 hover:text-yellow-400 border border-cyber-border rounded transition-all uppercase tracking-wider font-bold text-[9px] font-sfpro"
                          >
                            Inspect Details
                          </button>
                          <button
                            onClick={() => handleDeletePayment(pay.id)}
                            className="p-1.5 bg-red-950/30 border border-red-500/30 text-red-400 rounded hover:bg-red-900/50 hover:text-red-300 transition-colors"
                            title="Permanently Delete Payment"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right Column: Payload Inspection */}
        <div className="glass-panel p-6 rounded-xl border border-cyber-border/80 lg:col-span-1 space-y-4">
          <h2 className={`${headingStyle} text-lg`}>Raw Transaction Data</h2>
          
          {selectedPayload ? (
            <div className="space-y-4">
              <div className="p-3 bg-cyber-bg border border-cyber-border/60 rounded-lg flex items-center justify-between text-[10px] text-gray-500 font-mono">
                <span>EVENT TYPE:</span>
                <span className="text-yellow-400 font-bold">{selectedPayload.event || 'payment.captured'}</span>
              </div>
              <pre className="p-4 bg-cyber-bg border border-cyber-border rounded-lg text-[10px] font-mono text-gray-400 max-h-[360px] overflow-y-auto leading-relaxed whitespace-pre-wrap select-all">
                {JSON.stringify(selectedPayload, null, 2)}
              </pre>
            </div>
          ) : (
            <div className="py-16 text-center text-gray-600 uppercase tracking-widest text-[10px] font-mono">
              <Database className="w-10 h-10 mx-auto mb-3 text-gray-700 animate-bounce" />
              <span>Select a payment transaction to see its full raw receipt data.</span>
            </div>
          )}
        </div>

      </div>
    </div>
  )
}
