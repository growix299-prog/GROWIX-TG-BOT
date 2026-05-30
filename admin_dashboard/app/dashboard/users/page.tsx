"use client"

import { useEffect, useState } from 'react'
import { supabase } from '../../../lib/supabaseClient'
import { Search, RefreshCw, Trash2, Eye, Plus, RotateCcw, X, Users, Wallet, ShoppingCart, ArrowDownCircle } from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || 'https://nexautomate.onrender.com'
const ADMIN_KEY = process.env.NEXT_PUBLIC_ADMIN_API_KEY || 'nexus_admin_secret_key_2026_ultra_secure'

export default function UsersPage() {
  const [users, setUsers] = useState<any[]>([])
  const [filtered, setFiltered] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [balanceFilter, setBalanceFilter] = useState('ALL')
  const [selectedUser, setSelectedUser] = useState<any>(null)
  const [modalTab, setModalTab] = useState<'orders'|'transactions'>('orders')
  const [actionModal, setActionModal] = useState<{type: 'add'|null, user: any}>({type: null, user: null})
  const [actionAmount, setActionAmount] = useState('')
  const [actionDesc, setActionDesc] = useState('')
  const [actionLoading, setActionLoading] = useState(false)

  const fetchUsers = async () => {
    setLoading(true)
    try {
      const usersResp = await supabase.from('users').select('*').order('created_at', { ascending: false })
      const allUsers = usersResp.data || []
      for (const u of allUsers) {
        const ordersResp = await supabase.from('orders').select('id, amount, status, delivery_status, created_at, products(name, category)').eq('telegram_id', u.telegram_id).order('created_at', { ascending: false })
        u.orders = ordersResp.data || []
        u.total_orders = u.orders.length
        u.total_spent = u.orders.filter((o: any) => o.status === 'COMPLETED').reduce((s: number, o: any) => s + parseFloat(o.amount || 0), 0)
        
        // Enrich wallet transactions with detailed Razorpay data
        const txnResp = await supabase.from('wallet_transactions').select('*').eq('telegram_id', u.telegram_id).order('created_at', { ascending: false })
        const txns = txnResp.data || []
        
        // Fetch matching payments for detailed info
        for (const t of txns) {
          if (t.reference_id && t.reference_id.startsWith('pay_')) {
            const payResp = await supabase.from('payments').select('payload').eq('razorpay_payment_id', t.reference_id).limit(1)
            if (payResp.data && payResp.data.length > 0) {
              try {
                const method = payResp.data[0].payload?.payload?.payment?.entity?.method
                const vpa = payResp.data[0].payload?.payload?.payment?.entity?.vpa
                const email = payResp.data[0].payload?.payload?.payment?.entity?.email
                t.payment_details = `Method: ${method || 'Unknown'}` + (vpa ? ` | UPI: ${vpa}` : '') + (email ? ` | Email: ${email}` : '')
              } catch(e) {}
            }
          }
        }
        u.wallet_transactions = txns
      }
      setUsers(allUsers)
      setFiltered(allUsers)
    } catch (e: any) { console.error(e) }
    setLoading(false)
  }

  useEffect(() => { fetchUsers() }, [])

  useEffect(() => {
    let r = users
    if (search.trim()) {
      const q = search.toLowerCase()
      r = r.filter(u => String(u.telegram_id).includes(q) || (u.username||'').toLowerCase().includes(q) || (u.first_name||'').toLowerCase().includes(q))
    }
    if (balanceFilter === 'HAS') r = r.filter(u => parseFloat(u.wallet_balance||0) > 0)
    if (balanceFilter === 'ZERO') r = r.filter(u => parseFloat(u.wallet_balance||0) === 0)
    setFiltered(r)
  }, [search, balanceFilter, users])

  const totalBalance = users.reduce((s, u) => s + parseFloat(u.wallet_balance || 0), 0)
  const totalDeposits = users.reduce((s, u) => s + (u.wallet_transactions || []).filter((t: any) => t.transaction_type === 'DEPOSIT').reduce((a: number, t: any) => a + parseFloat(t.amount || 0), 0), 0)
  const totalRefunds = users.reduce((s, u) => s + (u.wallet_transactions || []).filter((t: any) => t.transaction_type === 'REFUND').reduce((a: number, t: any) => a + parseFloat(t.amount || 0), 0), 0)

  const handleDelete = async (tgId: number) => {
    if (!window.confirm(`Permanently delete user ${tgId} and ALL related data (orders, transactions, reviews)?`)) return
    try {
      const { error } = await supabase.rpc('admin_delete_user', { target_tg_id: tgId })
      
      if (error) {
        alert('Delete failed: ' + error.message)
        return
      }
      
      // Optimistic update for instant UI feedback (cast to String for safe comparison)
      setUsers(prev => prev.filter(u => String(u.telegram_id) !== String(tgId)))
      setFiltered(prev => prev.filter(u => String(u.telegram_id) !== String(tgId)))
      
      alert('User successfully deleted.')
      // Optionally still fetch in background
      fetchUsers()
    } catch (e: any) { alert('Delete failed: ' + e.message) }
  }

  const handleWalletAction = async () => {
    if (!actionModal.user || !actionAmount || parseFloat(actionAmount) <= 0) return
    setActionLoading(true)
    const tgId = actionModal.user.telegram_id
    const amt = parseFloat(actionAmount)
    try {
      const res = await fetch(`${API_BASE}/api/admin/users/${tgId}/add-funds`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Admin-API-Key': ADMIN_KEY
        },
        body: JSON.stringify({
          amount: amt,
          description: actionDesc || `Admin credit of ₹${amt.toFixed(2)}`
        })
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Failed to add funds')
      
      setActionModal({type: null, user: null})
      setActionAmount('')
      setActionDesc('')
      fetchUsers()
    } catch (e: any) { alert('Action failed: ' + e.message) }
    setActionLoading(false)
  }

  const h = "font-playfair font-black tracking-wide text-white"
  const statCard = (icon: any, label: string, value: string, color: string) => (
    <div className="bg-cyber-fbi/60 border border-cyber-border rounded-xl p-5 flex items-center gap-4">
      <div className={`w-12 h-12 rounded-lg ${color} flex items-center justify-center`}>{icon}</div>
      <div><p className="text-[10px] text-gray-500 uppercase tracking-widest font-bold font-sfpro">{label}</p><p className="text-xl font-black text-white font-playfair">{value}</p></div>
    </div>
  )

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div><h1 className={`${h} text-3xl`}>Users & Wallet Management</h1><p className="text-xs text-gray-500 font-sfpro mt-1 uppercase tracking-widest font-bold">Complete user profiles, wallet balances, transactions & orders</p></div>
        <button onClick={fetchUsers} className="p-2.5 bg-cyber-fbi border border-cyber-border hover:border-yellow-500/40 rounded-lg text-gray-400 hover:text-yellow-400 transition-all"><RefreshCw className="w-4 h-4" /></button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {statCard(<Users className="w-6 h-6 text-blue-400"/>, 'Total Users', String(users.length), 'bg-blue-950')}
        {statCard(<Wallet className="w-6 h-6 text-emerald-400"/>, 'Total Wallet Balance', `₹${totalBalance.toFixed(2)}`, 'bg-emerald-950')}
        {statCard(<ArrowDownCircle className="w-6 h-6 text-yellow-400"/>, 'Total Deposits', `₹${totalDeposits.toFixed(2)}`, 'bg-yellow-950')}
      </div>

      {/* Filters */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-sfpro">
        <div className="md:col-span-2 relative">
          <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"><Search className="h-4 w-4 text-yellow-500/40"/></span>
          <input type="text" value={search} onChange={e => setSearch(e.target.value)} placeholder="Search by Telegram ID, Username, or Name..." className="w-full pl-10 pr-4 py-2.5 bg-cyber-card border border-cyber-border rounded-lg text-cyber-text placeholder-gray-600 focus:outline-none focus:border-yellow-400"/>
        </div>
        <select value={balanceFilter} onChange={e => setBalanceFilter(e.target.value)} className="w-full px-4 py-2.5 bg-cyber-card border border-cyber-border rounded-lg text-cyber-text focus:outline-none focus:border-yellow-400">
          <option value="ALL">All Users</option>
          <option value="HAS">Has Wallet Balance</option>
          <option value="ZERO">Zero Balance</option>
        </select>
      </div>

      {/* Table */}
      {loading ? (
        <div className="h-96 flex items-center justify-center"><div className="w-8 h-8 border-2 border-yellow-500 border-t-transparent rounded-full animate-spin"></div></div>
      ) : (
        <div className="glass-panel rounded-xl border border-cyber-border/80 overflow-hidden shadow-glass">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead><tr className="border-b border-cyber-border text-gray-400 font-sfpro bg-cyber-fbi/40">
                <th className="py-3.5 px-4 uppercase tracking-wider font-bold">Telegram ID</th>
                <th className="py-3.5 px-4 uppercase tracking-wider font-bold">Username</th>
                <th className="py-3.5 px-4 uppercase tracking-wider font-bold">Name</th>
                <th className="py-3.5 px-4 uppercase tracking-wider font-bold text-right">Wallet Balance</th>
                <th className="py-3.5 px-4 uppercase tracking-wider font-bold text-center">Orders</th>
                <th className="py-3.5 px-4 uppercase tracking-wider font-bold text-right">Total Spent</th>
                <th className="py-3.5 px-4 uppercase tracking-wider font-bold">Joined</th>
                <th className="py-3.5 px-4 uppercase tracking-wider font-bold text-center">Actions</th>
              </tr></thead>
              <tbody className="font-sfpro divide-y divide-cyber-border/30">
                {filtered.length === 0 ? (
                  <tr><td colSpan={8} className="py-16 text-center text-gray-500 uppercase tracking-widest text-[10px]"><Users className="w-12 h-12 mx-auto mb-4 text-gray-600 animate-pulse"/>No users found</td></tr>
                ) : filtered.map(u => (
                  <tr key={u.id} className="hover:bg-cyber-card/30 transition-all font-medium">
                    <td className="py-4 px-4 font-bold text-yellow-400"><code>{u.telegram_id}</code></td>
                    <td className="py-4 px-4 text-gray-400">@{u.username || 'N/A'}</td>
                    <td className="py-4 px-4 font-bold text-white">{u.first_name || 'N/A'}</td>
                    <td className="py-4 px-4 text-right font-bold text-emerald-400">₹{parseFloat(u.wallet_balance||0).toFixed(2)}</td>
                    <td className="py-4 px-4 text-center"><span className="px-2 py-0.5 rounded bg-yellow-950/70 text-yellow-400 border border-yellow-500/10 text-[9px] font-bold">{u.total_orders}</span></td>
                    <td className="py-4 px-4 text-right text-gray-300">₹{(u.total_spent||0).toFixed(2)}</td>
                    <td className="py-4 px-4 text-gray-500">{(u.created_at||'').slice(0,10)}</td>
                    <td className="py-4 px-4 text-center flex gap-1.5 justify-center">
                      <button onClick={() => { setSelectedUser(u); setModalTab('orders') }} className="p-1.5 bg-blue-950/30 border border-blue-500/30 text-blue-400 rounded hover:bg-blue-900/50 transition-colors" title="View Details"><Eye className="w-4 h-4"/></button>
                      <button onClick={() => setActionModal({type:'add', user:u})} className="p-1.5 bg-emerald-950/30 border border-emerald-500/30 text-emerald-400 rounded hover:bg-emerald-900/50 transition-colors" title="Add Funds"><Plus className="w-4 h-4"/></button>
                      <button onClick={() => handleDelete(u.telegram_id)} className="p-1.5 bg-red-950/30 border border-red-500/30 text-red-400 rounded hover:bg-red-900/50 transition-colors" title="Delete User"><Trash2 className="w-4 h-4"/></button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* User Detail Modal */}
      {selectedUser && (
        <div className="fixed inset-0 pl-64 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-[100]" onClick={() => setSelectedUser(null)}>
          <div className="bg-cyber-bg border border-cyber-border rounded-2xl w-full max-w-4xl max-h-[85vh] overflow-y-auto relative z-[101]" onClick={e => e.stopPropagation()}>
            <div className="p-6 border-b border-cyber-border flex items-center justify-between">
              <div>
                <h2 className="text-lg font-black text-white font-playfair">{selectedUser.first_name || 'User'} — @{selectedUser.username || 'N/A'}</h2>
                <p className="text-xs text-gray-500 font-sfpro mt-1">TG ID: <code className="text-yellow-400">{selectedUser.telegram_id}</code> | Balance: <span className="text-emerald-400 font-bold">₹{parseFloat(selectedUser.wallet_balance||0).toFixed(2)}</span> | Orders: {selectedUser.total_orders} | Joined: {(selectedUser.created_at||'').slice(0,10)}</p>
              </div>
              <button onClick={() => setSelectedUser(null)} className="p-2 text-gray-400 hover:text-white"><X className="w-5 h-5"/></button>
            </div>
            {/* Tabs */}
            <div className="flex border-b border-cyber-border">
              <button onClick={() => setModalTab('orders')} className={`px-6 py-3 text-xs font-bold uppercase tracking-widest font-sfpro ${modalTab==='orders' ? 'text-yellow-400 border-b-2 border-yellow-400' : 'text-gray-500'}`}>Orders ({(selectedUser.orders||[]).length})</button>
              <button onClick={() => setModalTab('transactions')} className={`px-6 py-3 text-xs font-bold uppercase tracking-widest font-sfpro ${modalTab==='transactions' ? 'text-yellow-400 border-b-2 border-yellow-400' : 'text-gray-500'}`}>Wallet Transactions ({(selectedUser.wallet_transactions||[]).length})</button>
            </div>
            <div className="p-6">
              {modalTab === 'orders' ? (
                <table className="w-full text-left text-xs"><thead><tr className="border-b border-cyber-border text-gray-400 font-sfpro">
                  <th className="py-2 px-3">Product</th><th className="py-2 px-3">Category</th><th className="py-2 px-3 text-right">Amount</th><th className="py-2 px-3 text-center">Payment</th><th className="py-2 px-3 text-center">Delivery</th><th className="py-2 px-3">Date</th>
                </tr></thead><tbody className="divide-y divide-cyber-border/30">
                  {(selectedUser.orders||[]).length === 0 ? <tr><td colSpan={6} className="py-8 text-center text-gray-500">No orders</td></tr> :
                  (selectedUser.orders||[]).map((o: any) => (
                    <tr key={o.id} className="hover:bg-cyber-card/20">
                      <td className="py-3 px-3 font-bold text-white">{o.products?.name || 'N/A'}</td>
                      <td className="py-3 px-3"><span className={`px-2 py-0.5 rounded text-[9px] font-bold ${o.products?.category==='OTT'?'bg-purple-950/70 text-purple-400':'bg-yellow-950/70 text-yellow-400'}`}>{o.products?.category}</span></td>
                      <td className="py-3 px-3 text-right text-emerald-400 font-bold">₹{parseFloat(o.amount||0).toFixed(2)}</td>
                      <td className="py-3 px-3 text-center"><span className={`px-2 py-0.5 rounded text-[9px] font-bold ${o.status==='COMPLETED'?'bg-emerald-950 text-emerald-400':'bg-yellow-950 text-yellow-500'}`}>{o.status}</span></td>
                      <td className="py-3 px-3 text-center"><span className={`px-2 py-0.5 rounded text-[9px] font-bold ${o.delivery_status==='DELIVERED'?'bg-emerald-950 text-emerald-400':'bg-yellow-950 text-yellow-500'}`}>{o.delivery_status}</span></td>
                      <td className="py-3 px-3 text-gray-500">{(o.created_at||'').slice(0,10)}</td>
                    </tr>
                  ))}
                </tbody></table>
              ) : (
                <table className="w-full text-left text-xs"><thead><tr className="border-b border-cyber-border text-gray-400 font-sfpro">
                  <th className="py-2 px-3">Type</th><th className="py-2 px-3 text-right">Amount</th><th className="py-2 px-3">Description</th><th className="py-2 px-3">Reference</th><th className="py-2 px-3">Date</th>
                </tr></thead><tbody className="divide-y divide-cyber-border/30">
                  {(selectedUser.wallet_transactions||[]).length === 0 ? <tr><td colSpan={5} className="py-8 text-center text-gray-500">No transactions</td></tr> :
                  (selectedUser.wallet_transactions||[]).map((t: any) => (
                    <tr key={t.id} className="hover:bg-cyber-card/20">
                      <td className="py-3 px-3"><span className={`px-2 py-0.5 rounded text-[9px] font-bold ${t.transaction_type==='DEPOSIT'?'bg-emerald-950 text-emerald-400':t.transaction_type==='REFUND'?'bg-purple-950 text-purple-400':'bg-red-950 text-red-400'}`}>{t.transaction_type}</span></td>
                      <td className={`py-3 px-3 text-right font-bold ${t.transaction_type==='PURCHASE'?'text-red-400':'text-emerald-400'}`}>{t.transaction_type==='PURCHASE'?'-':'+'} ₹{parseFloat(t.amount||0).toFixed(2)}</td>
                      <td className="py-3 px-3 text-gray-300">
                        {t.description || '-'}
                        {t.payment_details && <div className="text-[9px] text-yellow-500 mt-1">{t.payment_details}</div>}
                      </td>
                      <td className="py-3 px-3 text-yellow-400 font-mono text-[10px]">{t.reference_id || '-'}</td>
                      <td className="py-3 px-3 text-gray-500">{(t.created_at||'').slice(0,10)}</td>
                    </tr>
                  ))}
                </tbody></table>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Add Funds Modal */}
      {actionModal.type === 'add' && (
        <div className="fixed inset-0 pl-64 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-[100]" onClick={() => setActionModal({type:null,user:null})}>
          <div className="bg-cyber-bg border border-cyber-border rounded-2xl w-full max-w-md relative z-[101]" onClick={e => e.stopPropagation()}>
            <div className="p-6 border-b border-cyber-border">
              <h2 className="text-lg font-black text-white font-playfair">➕ Add Funds</h2>
              <p className="text-xs text-gray-500 mt-1 font-sfpro">User: <code className="text-yellow-400">{actionModal.user.telegram_id}</code> — {actionModal.user.first_name || 'N/A'}</p>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="text-xs text-gray-400 font-sfpro font-bold uppercase tracking-wider">Amount (₹)</label>
                <input type="number" min="1" value={actionAmount} onChange={e => setActionAmount(e.target.value)} placeholder="Enter amount" className="w-full mt-1 px-4 py-2.5 bg-cyber-card border border-cyber-border rounded-lg text-cyber-text focus:outline-none focus:border-yellow-400 text-sm"/>
              </div>
              <div>
                <label className="text-xs text-gray-400 font-sfpro font-bold uppercase tracking-wider">Description (optional)</label>
                <input type="text" value={actionDesc} onChange={e => setActionDesc(e.target.value)} placeholder="Reason for action" className="w-full mt-1 px-4 py-2.5 bg-cyber-card border border-cyber-border rounded-lg text-cyber-text focus:outline-none focus:border-yellow-400 text-sm"/>
              </div>
              <div className="flex gap-3">
                <button onClick={() => setActionModal({type:null,user:null})} className="flex-1 py-2.5 bg-cyber-card border border-cyber-border rounded-lg text-gray-400 text-xs font-bold hover:text-white transition-all">Cancel</button>
                <button onClick={handleWalletAction} disabled={actionLoading || !actionAmount} className="flex-1 py-2.5 rounded-lg text-xs font-bold transition-all bg-emerald-950 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-900 disabled:opacity-50">
                  {actionLoading ? 'Processing...' : 'Add Funds'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
