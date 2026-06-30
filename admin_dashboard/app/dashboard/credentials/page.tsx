"use client"

import { useEffect, useState } from 'react'
import { supabase } from '../../../lib/supabaseClient'
import { KeyRound, Plus, Database, Sparkles, AlertCircle, RefreshCw, Trash2, Edit2, Check, X, ShieldAlert } from 'lucide-react'

export default function CredentialsPage() {
  const [credentials, setCredentials] = useState<any[]>([])
  const [products, setProducts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [uploadMode, setUploadMode] = useState<'single' | 'bulk'>('single')
  
  // Single form
  const [productId, setProductId] = useState('')
  const [emailOrUsername, setEmailOrUsername] = useState('')
  const [password, setPassword] = useState('')
  const [subscriptionMonths, setSubscriptionMonths] = useState('1')
  const [currentTime, setCurrentTime] = useState(new Date())
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 60000)
    return () => clearInterval(timer)
  }, [])
  
  // Bulk form
  const [bulkText, setBulkText] = useState('')
  const [bulkSeparator, setBulkSeparator] = useState(':') // ':' or ',' or '|'
  const [bulkSubscriptionMonths, setBulkSubscriptionMonths] = useState('1')

  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  // Edit Credential Modal States
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [editingCred, setEditingCred] = useState<any | null>(null)
  const [editEmail, setEditEmail] = useState('')
  const [editPassword, setEditPassword] = useState('')
  const [editStatus, setEditStatus] = useState('UNUSED')
  const [editProductId, setEditProductId] = useState('')
  const [editSubscriptionMonths, setEditSubscriptionMonths] = useState('1')
  const [editError, setEditError] = useState<string | null>(null)

  // Undo Delete States for Credentials
  const [undoCred, setUndoCred] = useState<any | null>(null)
  const [undoSeconds, setUndoSeconds] = useState(5)
  const [activeTimer, setActiveTimer] = useState<any>(null)

  const fetchData = async () => {
    try {
      setLoading(true)
      
      // Fetch credentials with products
      const { data: credsData } = await supabase
        .from('credentials')
        .select('*, products(name, category)')
        .order('created_at', { ascending: false })
      
      setCredentials(credsData || [])

      // Fetch products for dropdown (specifically Games or AUTO items)
      const { data: prodsData } = await supabase
        .from('products')
        .select('*')
        .eq('active', true)
      
      setProducts(prodsData || [])
      if (prodsData && prodsData.length > 0 && !productId) {
        setProductId(prodsData[0].id)
      }
    } catch (err: any) {
      console.error(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    return () => {
      if (activeTimer) clearInterval(activeTimer)
    }
  }, [])

  const openEditCredModal = (cred: any) => {
    setEditingCred(cred)
    setEditEmail(cred.email_or_username)
    setEditPassword(cred.password)
    setEditStatus(cred.status)
    setEditProductId(cred.product_id)
    setEditSubscriptionMonths(cred.subscription_months?.toString() || '1')
    setEditError(null)
    setIsEditModalOpen(true)
  }

  const handleSaveEditCred = async (e: React.FormEvent) => {
    e.preventDefault()
    setEditError(null)

    if (!editEmail.trim() || !editPassword.trim() || !editProductId) {
      setEditError("All fields are required.")
      return
    }

    try {
      const { error } = await supabase
        .from('credentials')
        .update({
          email_or_username: editEmail.trim(),
          password: editPassword.trim(),
          status: editStatus,
          product_id: editProductId,
          subscription_months: parseInt(editSubscriptionMonths) || 1
        })
        .eq('id', editingCred.id)

      if (error) throw error
      setIsEditModalOpen(false)
      fetchData()
    } catch (err: any) {
      setEditError(err.message)
    }
  }

  const startSoftDeleteCred = (cred: any) => {
    if (undoCred) {
      commitDeleteCred(undoCred.id)
    }

    setUndoCred(cred)
    setCredentials((prev) => prev.filter((c) => c.id !== cred.id))
    setUndoSeconds(5)

    if (activeTimer) clearInterval(activeTimer)

    let secondsLeft = 5
    const timer = setInterval(() => {
      secondsLeft -= 1
      setUndoSeconds(secondsLeft)
      if (secondsLeft <= 0) {
        clearInterval(timer)
        commitDeleteCred(cred.id)
      }
    }, 1000)

    setActiveTimer(timer)
  }

  const triggerUndoCred = () => {
    if (activeTimer) clearInterval(activeTimer)
    if (undoCred) {
      setCredentials((prev) => [undoCred, ...prev])
      setUndoCred(null)
      setActiveTimer(null)
    }
  }

  const commitDeleteCred = async (id: string) => {
    try {
      const { error } = await supabase
        .from('credentials')
        .delete()
        .eq('id', id)
      if (error) throw error
    } catch (err: any) {
      console.error("Delete failed: ", err.message)
    } finally {
      setUndoCred(null)
      setActiveTimer(null)
    }
  }

  const handleSingleSubmit = async (e: React.FormEvent) => {
    const selectedProduct = products.find(p => p.id === productId);
    const hasDuration = selectedProduct?.category === 'OTT' || selectedProduct?.category === 'VideoEditing';
    e.preventDefault()
    setMessage(null)

    if (!productId || !emailOrUsername.trim() || !password.trim()) {
      setMessage({ type: 'error', text: 'Please fill in all security fields.' })
      return
    }

    try {
      const { error } = await supabase
        .from('credentials')
        .insert([{
          product_id: productId,
          email_or_username: emailOrUsername.trim(),
          password: password.trim(),
          status: 'UNUSED',
          subscription_months: hasDuration ? parseInt(subscriptionMonths) || 1 : 0
        }])

      if (error) throw error
      
      setMessage({ type: 'success', text: 'Account added successfully to stock inventory!' })
      setEmailOrUsername('')
      setPassword('')
      fetchData()
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message })
    }
  }

  const handleBulkSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const selectedProduct = products.find(p => p.id === productId);
    const hasDuration = selectedProduct?.category === 'OTT' || selectedProduct?.category === 'VideoEditing';
    setMessage(null)

    if (!productId || !bulkText.trim()) {
      setMessage({ type: 'error', text: 'Please provide bulk data to load.' })
      return
    }

    const lines = bulkText.split('\n')
    const insertPayload: any[] = []
    let failedLinesCount = 0

    lines.forEach((line) => {
      const cleanLine = line.trim()
      if (!cleanLine) return

      const parts = cleanLine.split(bulkSeparator)
      if (parts.length >= 2) {
        let pass = parts.slice(1).join(bulkSeparator).trim();
        let months = hasDuration ? parseInt(bulkSubscriptionMonths) || 1 : 0;

        insertPayload.push({
          product_id: productId,
          email_or_username: parts[0].trim(),
          password: pass,
          status: 'UNUSED',
          subscription_months: months
        })
      } else {
        failedLinesCount++
      }
    })

    if (insertPayload.length === 0) {
      setMessage({ type: 'error', text: 'Failed to parse any valid accounts. Check separator.' })
      return
    }

    try {
      const { error } = await supabase
        .from('credentials')
        .insert(insertPayload)

      if (error) throw error

      let alertMsg = `Bulk upload complete! ${insertPayload.length} accounts added to stock inventory.`
      if (failedLinesCount > 0) {
        alertMsg += ` (${failedLinesCount} lines failed parsing).`
      }

      setMessage({ type: 'success', text: alertMsg })
      setBulkText('')
      fetchData()
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message })
    }
  }

  const headingStyle = "font-playfair font-black tracking-wide text-white"

  return (
    <div className="space-y-8">
      {/* Dynamic Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className={`${headingStyle} text-3xl`}>Accounts Inventory</h1>
          <p className="text-xs text-gray-500 font-sfpro mt-1 uppercase tracking-widest">Stock accounts and manage active digital items</p>
        </div>
        <button
          onClick={fetchData}
          className="p-2.5 bg-cyber-fbi border border-cyber-border hover:border-yellow-500/40 rounded-lg text-gray-400 hover:text-yellow-400 transition-all"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* LEFT COLUMN: Feed Form */}
        <div className="glass-panel p-6 rounded-xl border border-cyber-border/80 h-fit lg:col-span-1 space-y-6">
          <div className="flex border-b border-cyber-border/40 pb-3">
            <button
              onClick={() => setUploadMode('single')}
              className={`w-1/2 py-2 text-xs font-bold uppercase tracking-wider font-sfpro transition-all border-b-2 ${
                uploadMode === 'single' ? 'border-yellow-500 text-yellow-400 font-black' : 'border-transparent text-gray-500'
              }`}
            >
              Single Feed
            </button>
            <button
              onClick={() => setUploadMode('bulk')}
              className={`w-1/2 py-2 text-xs font-bold uppercase tracking-wider font-sfpro transition-all border-b-2 ${
                uploadMode === 'bulk' ? 'border-yellow-500 text-yellow-400 font-black' : 'border-transparent text-gray-500'
              }`}
            >
              Bulk Upload
            </button>
          </div>

          {message && (
            <div className={`p-3 border rounded-lg text-xs flex items-center gap-2 font-sfpro ${
              message.type === 'success' 
                ? 'bg-emerald-950/60 border-emerald-500/20 text-emerald-400 shadow-glow-green/10' 
                : 'bg-red-950/60 border-red-500/20 text-red-400 shadow-glow-red/10'
            }`}>
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{message.text}</span>
            </div>
          )}

          <div className="space-y-4 text-xs font-sfpro">
            <div>
              <label className="block text-[10px] uppercase tracking-wider text-gray-400 font-bold mb-1">Target Product</label>
              {products.length === 0 ? (
                <div className="p-3 bg-yellow-950/40 border border-yellow-500/20 rounded-lg text-yellow-400 text-[11px] leading-relaxed">
                  ⚠️ <b>No Products Found!</b> Go to the <b>Product Catalog</b> tab first and add a product (like GTA V or Netflix). Once you add a product, it will show up here so you can add accounts for it!
                </div>
              ) : (
                <select
                  value={productId}
                  onChange={(e) => setProductId(e.target.value)}
                  className="w-full px-4 py-2.5 bg-cyber-bg border border-cyber-border rounded-lg text-cyber-text focus:outline-none focus:border-yellow-400"
                >
                  {products.map((prod) => (
                    <option key={prod.id} value={prod.id}>
                      {prod.name} ({prod.category})
                    </option>
                  ))}
                </select>
              )}
            </div>

            {uploadMode === 'single' ? (
              <form onSubmit={handleSingleSubmit} className="space-y-4">
                <div>
                  <label className="block text-[10px] uppercase tracking-wider text-gray-400 font-bold mb-1">Login Username or Email</label>
                  <input
                    type="text"
                    required
                    autoComplete="off"
                    value={emailOrUsername}
                    onChange={(e) => setEmailOrUsername(e.target.value)}
                    placeholder="account@gmail.com"
                    className="w-full px-4 py-2.5 bg-cyber-bg border border-cyber-border rounded-lg text-cyber-text placeholder-gray-600 focus:outline-none focus:border-yellow-400"
                  />
                </div>
                <div>
                  <label className="block text-[10px] uppercase tracking-wider text-gray-400 font-bold mb-1">Passcode/Password</label>
                  <input
                    type="text"
                    required
                    autoComplete="off"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter account password..."
                    className="w-full px-4 py-2.5 bg-cyber-bg border border-cyber-border rounded-lg text-cyber-text placeholder-gray-600 focus:outline-none focus:border-yellow-400"
                  />
                </div>
                {(products.find(p => p.id === productId)?.category === 'OTT' || products.find(p => p.id === productId)?.category === 'VideoEditing') && (
                  <div>
                    <label className="block text-[10px] uppercase tracking-wider text-gray-400 font-bold mb-1">Subscription Duration (Months)</label>
                    <div className="flex gap-2 mb-2">
                        <button type="button" onClick={() => setSubscriptionMonths('1')} className={`flex-1 py-1.5 text-xs font-bold uppercase tracking-wider border rounded transition-all ${subscriptionMonths === '1' ? 'border-cyan-500 text-cyan-400 bg-cyan-950/40 shadow-[0_0_10px_rgba(34,211,238,0.2)]' : 'border-cyber-border text-gray-500 hover:border-gray-500 hover:text-gray-300'}`}>1 Month</button>
                        <button type="button" onClick={() => setSubscriptionMonths('3')} className={`flex-1 py-1.5 text-xs font-bold uppercase tracking-wider border rounded transition-all ${subscriptionMonths === '3' ? 'border-yellow-500 text-yellow-400 bg-yellow-950/40 shadow-[0_0_10px_rgba(234,179,8,0.2)]' : 'border-cyber-border text-gray-500 hover:border-gray-500 hover:text-gray-300'}`}>3 Months</button>
                        <button type="button" onClick={() => setSubscriptionMonths('6')} className={`flex-1 py-1.5 text-xs font-bold uppercase tracking-wider border rounded transition-all ${subscriptionMonths === '6' ? 'border-rose-500 text-rose-400 bg-rose-950/40 shadow-[0_0_10px_rgba(244,63,94,0.2)]' : 'border-cyber-border text-gray-500 hover:border-gray-500 hover:text-gray-300'}`}>6 Months</button>
                    </div>
                    <input
                      type="number"
                      min="1"
                      required
                      value={subscriptionMonths}
                      onChange={(e) => setSubscriptionMonths(e.target.value)}
                      placeholder="Or type custom months (e.g. 12)"
                      className="w-full px-4 py-2.5 bg-black border border-cyber-border rounded-lg text-cyber-text placeholder-gray-600 focus:outline-none focus:border-yellow-400"
                    />
                  </div>
                )}
                <button
                  type="submit"
                  className="w-full py-2.5 bg-gradient-to-r from-yellow-600 to-teal-600 hover:from-yellow-500 hover:to-teal-500 text-white font-bold rounded-lg uppercase tracking-widest transition-all shadow-glow-yellow active:scale-[0.98]"
                >
                  Inject Account
                </button>
              </form>
            ) : (
              <form onSubmit={handleBulkSubmit} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[10px] uppercase tracking-wider text-gray-400 font-bold mb-1">Delimiter</label>
                    <select
                      value={bulkSeparator}
                      onChange={(e) => setBulkSeparator(e.target.value)}
                      className="w-full px-4 py-2 bg-cyber-bg border border-cyber-border rounded-lg text-cyber-text focus:outline-none focus:border-yellow-400"
                    >
                      <option value=":">Colon (:)</option>
                      <option value=",">Comma (,)</option>
                      <option value="|">Pipe (|)</option>
                    </select>
                  </div>
                  <div className="flex items-end text-[10px] text-gray-500 leading-tight">
                    Format line-by-line:<br/>
                    username{bulkSeparator}password
                  </div>
                </div>

                {(products.find(p => p.id === productId)?.category === 'OTT' || products.find(p => p.id === productId)?.category === 'VideoEditing') && (
                  <div>
                    <label className="block text-[10px] uppercase tracking-wider text-gray-400 font-bold mb-1">Apply Subscription Duration to all (Months)</label>
                    <div className="flex gap-2 mb-2">
                        <button type="button" onClick={() => setBulkSubscriptionMonths('1')} className={`flex-1 py-1.5 text-xs font-bold uppercase tracking-wider border rounded transition-all ${bulkSubscriptionMonths === '1' ? 'border-cyan-500 text-cyan-400 bg-cyan-950/40 shadow-[0_0_10px_rgba(34,211,238,0.2)]' : 'border-cyber-border text-gray-500 hover:border-gray-500 hover:text-gray-300'}`}>1 Month</button>
                        <button type="button" onClick={() => setBulkSubscriptionMonths('3')} className={`flex-1 py-1.5 text-xs font-bold uppercase tracking-wider border rounded transition-all ${bulkSubscriptionMonths === '3' ? 'border-yellow-500 text-yellow-400 bg-yellow-950/40 shadow-[0_0_10px_rgba(234,179,8,0.2)]' : 'border-cyber-border text-gray-500 hover:border-gray-500 hover:text-gray-300'}`}>3 Months</button>
                        <button type="button" onClick={() => setBulkSubscriptionMonths('6')} className={`flex-1 py-1.5 text-xs font-bold uppercase tracking-wider border rounded transition-all ${bulkSubscriptionMonths === '6' ? 'border-rose-500 text-rose-400 bg-rose-950/40 shadow-[0_0_10px_rgba(244,63,94,0.2)]' : 'border-cyber-border text-gray-500 hover:border-gray-500 hover:text-gray-300'}`}>6 Months</button>
                    </div>
                    <input
                      type="number"
                      min="1"
                      required
                      value={bulkSubscriptionMonths}
                      onChange={(e) => setBulkSubscriptionMonths(e.target.value)}
                      placeholder="Or type custom months (e.g. 12)"
                      className="w-full px-4 py-2 bg-black border border-cyber-border rounded-lg text-cyber-text placeholder-gray-600 focus:outline-none focus:border-yellow-400"
                    />
                  </div>
                )}

                <div>
                  <label className="block text-[10px] uppercase tracking-wider text-gray-400 font-bold mb-1">Bulk Account Matrix</label>
                  <textarea
                    rows={8}
                    required
                    value={bulkText}
                    onChange={(e) => setBulkText(e.target.value)}
                    placeholder={`acc1@gmail.com${bulkSeparator}pass123\nacc2@gmail.com${bulkSeparator}pass456`}
                    className="w-full px-4 py-2.5 bg-cyber-bg border border-cyber-border rounded-lg text-cyber-text font-mono placeholder-gray-600 focus:outline-none focus:border-yellow-400 leading-relaxed resize-none"
                  ></textarea>
                </div>

                <button
                  type="submit"
                  className="w-full py-2.5 bg-gradient-to-r from-yellow-600 to-teal-600 hover:from-yellow-500 hover:to-teal-500 text-white font-bold rounded-lg uppercase tracking-widest transition-all shadow-glow-yellow active:scale-[0.98]"
                >
                  Feed Bulk Accounts
                </button>
              </form>
            )}
          </div>
        </div>

        {/* RIGHT COLUMN: Inventory Audit */}
        <div className="glass-panel p-6 rounded-xl border border-cyber-border/80 lg:col-span-2 space-y-4">
          {/* Stock Summary Cards */}
          <h2 className={`${headingStyle} text-lg`}>Stock Summary</h2>
          <div className="flex overflow-x-auto gap-3 mb-4 pb-2 snap-x scrollbar-thin scrollbar-thumb-cyber-border scrollbar-track-transparent">
            {(() => {
              const stockMap: Record<string, {total: number, used: number, unused: number, productName: string}> = {}
              credentials.forEach((cred: any) => {
                const name = cred.products?.name || 'Unknown'
                if (!stockMap[name]) stockMap[name] = {total: 0, used: 0, unused: 0, productName: name}
                stockMap[name].total++
                if (cred.status === 'USED') stockMap[name].used++
                else stockMap[name].unused++
              })
              const entries = Object.values(stockMap).sort((a, b) => b.total - a.total)
              if (entries.length === 0) return <div className="text-gray-600 text-xs text-center py-4 w-full">No accounts in stock</div>
              return entries.map((entry) => (
                <div key={entry.productName} className="p-3 bg-cyber-bg border border-cyber-border/50 rounded-lg min-w-[160px] max-w-[200px] flex-shrink-0 snap-start">
                  <p className="text-white font-bold text-xs truncate mb-1">{entry.productName}</p>
                  <p className="text-lg font-black text-yellow-400">{entry.total} <span className="text-[10px] text-gray-500 font-normal">accounts</span></p>
                  <div className="flex gap-2 mt-1">
                    <span className="text-[10px] text-emerald-400 font-bold">{entry.unused} unused</span>
                    <span className="text-[10px] text-gray-500 font-bold">{entry.used} used</span>
                  </div>
                </div>
              ))
            })()}
          </div>

          <h2 className={`${headingStyle} text-lg`}>Accounts Stock Inventory Log</h2>
          
          <div className="overflow-x-auto max-h-[480px]">
            <table className="w-full min-w-[800px] text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-cyber-border text-gray-400 font-sfpro sticky top-0 bg-cyber-card/90 backdrop-blur-sm z-10">
                  <th className="py-3 px-4 uppercase tracking-wider font-bold">Product Item</th>
                  <th className="py-3 px-4 uppercase tracking-wider font-bold">Account / Email</th>
                  <th className="py-3 px-4 uppercase tracking-wider font-bold">Account Password</th>
                  <th className="py-3 px-4 uppercase tracking-wider font-bold text-center">Duration</th>
                  <th className="py-3 px-4 uppercase tracking-wider font-bold text-center">Status</th>
                  <th className="py-3 px-4 uppercase tracking-wider font-bold text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="font-sfpro divide-y divide-cyber-border/30">
                {credentials.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-12 text-center text-gray-500 uppercase tracking-widest text-[10px]">No accounts in Stock</td>
                  </tr>
                ) : (
                  // Group credentials by product name, then flatten
                  (() => {
                    const grouped: Record<string, any[]> = {}
                    credentials.forEach((cred: any) => {
                      const name = cred.products?.name || 'Unknown'
                      if (!grouped[name]) grouped[name] = []
                      grouped[name].push(cred)
                    })
                    const rows: JSX.Element[] = []
                    Object.entries(grouped).forEach(([productName, creds]) => {
                      // Product group header
                      const unused = creds.filter(c => c.status === 'UNUSED').length
                      const used = creds.filter(c => c.status === 'USED').length
                      rows.push(
                        <tr key={`header-${productName}`} className="bg-yellow-950/20 border-t-2 border-yellow-500/30">
                          <td colSpan={6} className="py-2 px-4 text-yellow-400 font-bold text-xs uppercase tracking-wider">
                            {productName} — <span className="text-emerald-400">{unused} unused</span> / <span className="text-gray-400">{used} used</span> / <span className="text-white">{creds.length} total</span>
                          </td>
                        </tr>
                      )
                      creds.forEach((cred) => {
                        rows.push(
                          <tr key={cred.id} className="hover:bg-cyber-card/3 group transition-all">
                            <td className="py-3 px-4 font-bold text-white">{cred.products?.name}</td>
                            <td className="py-3 px-4 font-mono text-gray-400">{cred.email_or_username}</td>
                            <td className="py-3 px-4 font-mono text-gray-500 group-hover:text-cyber-text transition-all select-all">
                              <code>{cred.password}</code>
                            </td>
                            <td className="py-3 px-4 text-center">
                              {cred.subscription_months ? (
                                <span className="text-[11px] font-bold text-cyan-400">{cred.subscription_months}M</span>
                              ) : <span className="text-gray-600">-</span>}
                            </td>
                            <td className="py-3 px-4 text-center">
                              <span className={`px-2 py-0.5 rounded text-[9px] font-bold ${
                                cred.status === 'UNUSED' 
                                  ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-500/20' 
                                  : 'bg-gray-900/80 text-gray-500 border border-cyber-border'
                              }`}>
                                {cred.status}
                              </span>
                            </td>
                            <td className="py-3 px-4 text-center">
                              <div className="flex items-center justify-center gap-2">
                                <button
                                  onClick={() => openEditCredModal(cred)}
                                  className="p-1 bg-cyber-bg hover:bg-yellow-950/30 text-gray-400 hover:text-yellow-400 border border-cyber-border rounded transition-all"
                                >
                                  <Edit2 className="w-3.5 h-3.5" />
                                </button>
                                <button
                                  onClick={() => startSoftDeleteCred(cred)}
                                  className="p-1 bg-cyber-bg hover:bg-red-950/30 text-gray-400 hover:text-red-400 border border-cyber-border rounded transition-all"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              </div>
                            </td>
                          </tr>
                        )
                      })
                    })
                    return rows
                  })()
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Edit Credential Modal */}
      {isEditModalOpen && (
        <div className="fixed inset-0 pl-64 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="w-full max-w-md glass-panel p-8 rounded-2xl glow-border-cyan shadow-glass relative text-xs font-sfpro text-white">
            <h2 className={`${headingStyle} text-xl mb-6`}>Modify Account Credentials</h2>

            {editError && (
              <div className="mb-4 p-3 bg-red-950/50 border border-red-500/30 rounded-lg text-red-400 text-xs flex items-center gap-2 font-sfpro">
                <ShieldAlert className="w-4.5 h-4.5 flex-shrink-0" />
                <span>{editError}</span>
              </div>
            )}

            <form onSubmit={handleSaveEditCred} className="space-y-5">
              <div>
                <label className="block text-[10px] uppercase tracking-wider text-gray-400 font-bold mb-1">Target Product</label>
                <select
                  value={editProductId}
                  onChange={(e) => setEditProductId(e.target.value)}
                  className="w-full px-4 py-2.5 bg-cyber-bg border border-cyber-border rounded-lg text-cyber-text focus:outline-none focus:border-yellow-400"
                >
                  {products.map((prod) => (
                    <option key={prod.id} value={prod.id}>
                      {prod.name} ({prod.category})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[10px] uppercase tracking-wider text-gray-400 font-bold mb-1">Account Username / Email</label>
                <input
                  type="text"
                  required
                  autoComplete="off"
                  value={editEmail}
                  onChange={(e) => setEditEmail(e.target.value)}
                  className="w-full px-4 py-2.5 bg-cyber-bg border border-cyber-border rounded-lg text-cyber-text focus:outline-none focus:border-yellow-400"
                />
              </div>

              <div>
                <label className="block text-[10px] uppercase tracking-wider text-gray-400 font-bold mb-1">Password</label>
                <input
                  type="text"
                  required
                  autoComplete="new-password"
                  value={editPassword}
                  onChange={(e) => setEditPassword(e.target.value)}
                  className="w-full px-4 py-2.5 bg-cyber-bg border border-cyber-border rounded-lg text-cyber-text focus:outline-none focus:border-yellow-400"
                />
              </div>

              {products.find(p => p.id === editProductId)?.category === 'OTT' && (
                <div>
                  <label className="block text-[10px] uppercase tracking-wider text-gray-400 font-bold mb-1">Subscription Duration (Months)</label>
                  <div className="flex gap-2 mb-2">
                      <button type="button" onClick={() => setEditSubscriptionMonths('1')} className={`flex-1 py-1.5 text-xs font-bold uppercase tracking-wider border rounded transition-all ${editSubscriptionMonths === '1' ? 'border-cyan-500 text-cyan-400 bg-cyan-950/40' : 'border-cyber-border text-gray-500 hover:border-gray-500'}`}>1 Month</button>
                      <button type="button" onClick={() => setEditSubscriptionMonths('3')} className={`flex-1 py-1.5 text-xs font-bold uppercase tracking-wider border rounded transition-all ${editSubscriptionMonths === '3' ? 'border-yellow-500 text-yellow-400 bg-yellow-950/40' : 'border-cyber-border text-gray-500 hover:border-gray-500'}`}>3 Months</button>
                      <button type="button" onClick={() => setEditSubscriptionMonths('6')} className={`flex-1 py-1.5 text-xs font-bold uppercase tracking-wider border rounded transition-all ${editSubscriptionMonths === '6' ? 'border-rose-500 text-rose-400 bg-rose-950/40' : 'border-cyber-border text-gray-500 hover:border-gray-500'}`}>6 Months</button>
                  </div>
                  <input
                    type="number"
                    min="1"
                    required
                    value={editSubscriptionMonths}
                    onChange={(e) => setEditSubscriptionMonths(e.target.value)}
                    placeholder="Or type custom months..."
                    className="w-full px-4 py-2.5 bg-black border border-cyber-border rounded-lg text-cyber-text focus:outline-none focus:border-yellow-400"
                  />
                </div>
              )}

              <div>
                <label className="block text-[10px] uppercase tracking-wider text-gray-400 font-bold mb-1">Status</label>
                <select
                  value={editStatus}
                  onChange={(e) => setEditStatus(e.target.value)}
                  className="w-full px-4 py-2.5 bg-cyber-bg border border-cyber-border rounded-lg text-cyber-text focus:outline-none focus:border-yellow-400"
                >
                  <option value="UNUSED">UNUSED (Available for sale)</option>
                  <option value="USED">USED (Already delivered)</option>
                </select>
              </div>

              <div className="flex gap-3 pt-4 border-t border-cyber-border/40">
                <button
                  type="button"
                  onClick={() => setIsEditModalOpen(false)}
                  className="w-1/2 py-2.5 bg-cyber-bg border border-cyber-border hover:bg-cyber-card text-gray-400 rounded-lg font-bold uppercase tracking-widest active:scale-[0.98] transition-all"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="w-1/2 py-2.5 bg-yellow-600 hover:bg-yellow-500 text-white rounded-lg font-bold uppercase tracking-widest shadow-glow-yellow active:scale-[0.98] transition-all"
                >
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 5-Second Undo Toast */}
      {undoCred && (
        <div className="fixed bottom-6 right-6 z-50 glass-panel px-6 py-4 rounded-xl border border-rose-500/30 shadow-glow-rose/10 flex items-center justify-between gap-6 animate-slide-up">
          <div className="flex items-center gap-3">
            <span className="h-2 w-2 rounded-full bg-rose-500 animate-ping"></span>
            <div className="text-xs font-sfpro">
              <p className="text-white font-bold">Deleted Account Stock</p>
              <p className="text-gray-400 text-[10px]">Permanent delete in <span className="text-rose-400 font-bold">{undoSeconds}s</span></p>
            </div>
          </div>
          <button
            onClick={triggerUndoCred}
            className="px-3 py-1 bg-yellow-950 border border-yellow-500/30 text-yellow-400 hover:text-cyan-300 font-bold uppercase text-[10px] tracking-wider rounded-lg transition-all active:scale-95"
          >
            Undo Delete
          </button>
        </div>
      )}
    </div>
  )
}
