"use client"

import { useEffect, useState } from 'react'
import { supabase } from '../../../lib/supabaseClient'
import { Megaphone, Send, Package, Users, AlertCircle, CheckCircle2, Loader2, Eye, Sparkles } from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || 'https://nexautomate.onrender.com'
const ADMIN_KEY = process.env.NEXT_PUBLIC_ADMIN_API_KEY || 'nexus_admin_secret_key_2026_ultra_secure'

// Product emoji helper (mirrors backend)
function getProductEmoji(name: string) {
  const n = name.toLowerCase()
  if (n.includes('netflix')) return '🔴'
  if (n.includes('prime')) return '🔵'
  if (n.includes('canva')) return '🖌️'
  if (n.includes('crunchyroll')) return '🟠'
  if (n.includes('spotify')) return '🟢'
  if (n.includes('duolingo')) return '🟢'
  if (n.includes('gta')) return '🚗'
  if (n.includes('valorant')) return '🎯'
  if (n.includes('nord') || n.includes('vpn')) return '🛡️'
  if (n.includes('tradingview')) return '📈'
  return '🔹'
}

export default function BroadcastPage() {
  const [products, setProducts] = useState<any[]>([])
  const [selectedProductId, setSelectedProductId] = useState('')
  const [stockAdded, setStockAdded] = useState<number>(0)
  const [customMessage, setCustomMessage] = useState('')
  const [totalStock, setTotalStock] = useState<number>(0)
  const [totalUsers, setTotalUsers] = useState<number>(0)
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [showPreview, setShowPreview] = useState(false)
  const [result, setResult] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  useEffect(() => {
    fetchData()
  }, [])

  useEffect(() => {
    if (selectedProductId) {
      fetchStockCount(selectedProductId)
    }
  }, [selectedProductId])

  const fetchData = async () => {
    try {
      setLoading(true)
      
      // Fetch active products
      const { data: prodsData } = await supabase
        .from('products')
        .select('*')
        .eq('active', true)
        .order('name')
      
      setProducts(prodsData || [])
      if (prodsData && prodsData.length > 0) {
        setSelectedProductId(prodsData[0].id)
      }

      // Fetch total users count
      const { count } = await supabase
        .from('users')
        .select('*', { count: 'exact', head: true })
      
      setTotalUsers(count || 0)
    } catch (err: any) {
      console.error(err.message)
    } finally {
      setLoading(false)
    }
  }

  const fetchStockCount = async (productId: string) => {
    try {
      const { count } = await supabase
        .from('credentials')
        .select('*', { count: 'exact', head: true })
        .eq('product_id', productId)
        .eq('status', 'UNUSED')
      
      setTotalStock(count || 0)
    } catch {
      setTotalStock(0)
    }
  }

  const selectedProduct = products.find(p => p.id === selectedProductId)

  const handleSendBroadcast = async () => {
    if (!selectedProductId || stockAdded <= 0) {
      setResult({ type: 'error', text: 'Please select a product and enter stock added count.' })
      return
    }

    setSending(true)
    setResult(null)

    try {
      const res = await fetch(`${API_BASE}/api/admin/broadcast-stock`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Admin-API-Key': ADMIN_KEY
        },
        body: JSON.stringify({
          product_id: selectedProductId,
          stock_added: stockAdded,
          custom_message: customMessage || undefined
        })
      })

      const data = await res.json()

      if (res.ok) {
        setResult({
          type: 'success',
          text: `✅ Broadcast sent! ${data.total_users} users will receive the stock alert for ${data.product}.`
        })
        setStockAdded(0)
        setCustomMessage('')
        setShowPreview(false)
      } else {
        setResult({ type: 'error', text: data.detail || 'Failed to send broadcast' })
      }
    } catch (err: any) {
      setResult({ type: 'error', text: err.message || 'Network error' })
    } finally {
      setSending(false)
    }
  }

  const headingStyle = "font-playfair font-black tracking-wide text-white"

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 text-yellow-400 animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className={`${headingStyle} text-3xl flex items-center gap-3`}>
            <Megaphone className="w-8 h-8 text-yellow-400" />
            Stock Broadcast
          </h1>
          <p className="text-xs text-gray-500 font-sfpro mt-1 uppercase tracking-widest">
            Send stock alerts to all bot users instantly
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="glass-panel px-4 py-2.5 rounded-lg border border-cyber-border/60 flex items-center gap-2">
            <Users className="w-4 h-4 text-yellow-400" />
            <span className="text-xs font-sfpro text-gray-400">Total Users:</span>
            <span className="text-sm font-bold text-white font-sfpro">{totalUsers}</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* LEFT: Broadcast Form */}
        <div className="glass-panel p-6 rounded-xl border border-cyber-border/80 space-y-6">
          <div className="flex items-center gap-2 border-b border-cyber-border/40 pb-3">
            <Send className="w-4 h-4 text-yellow-400" />
            <h2 className={`${headingStyle} text-lg`}>Compose Broadcast</h2>
          </div>

          {result && (
            <div className={`p-3 border rounded-lg text-xs flex items-center gap-2 font-sfpro ${
              result.type === 'success'
                ? 'bg-emerald-950/60 border-emerald-500/20 text-emerald-400'
                : 'bg-red-950/60 border-red-500/20 text-red-400'
            }`}>
              {result.type === 'success' ? <CheckCircle2 className="w-4 h-4 flex-shrink-0" /> : <AlertCircle className="w-4 h-4 flex-shrink-0" />}
              <span>{result.text}</span>
            </div>
          )}

          <div className="space-y-5 text-xs font-sfpro">
            {/* Product Selection */}
            <div>
              <label className="block text-[10px] uppercase tracking-wider text-gray-400 font-bold mb-1.5">
                Select Product
              </label>
              {products.length === 0 ? (
                <div className="p-3 bg-yellow-950/40 border border-yellow-500/20 rounded-lg text-yellow-400 text-[11px]">
                  ⚠️ No active products found. Add products first.
                </div>
              ) : (
                <select
                  value={selectedProductId}
                  onChange={(e) => setSelectedProductId(e.target.value)}
                  className="w-full px-4 py-2.5 bg-cyber-bg border border-cyber-border rounded-lg text-cyber-text focus:outline-none focus:border-yellow-400"
                >
                  {products.map((prod) => (
                    <option key={prod.id} value={prod.id}>
                      {getProductEmoji(prod.name)} {prod.name} ({prod.category}) — ₹{parseFloat(prod.price).toFixed(2)}
                    </option>
                  ))}
                </select>
              )}
            </div>

            {/* Stock Info Cards */}
            {selectedProduct && (
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-cyber-bg/70 border border-cyber-border/40 rounded-lg text-center">
                  <p className="text-[10px] text-gray-500 uppercase tracking-wider font-bold">Current Stock</p>
                  <p className={`text-xl font-black mt-1 ${totalStock > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {totalStock}
                  </p>
                  <p className="text-[10px] text-gray-600 mt-0.5">UNUSED accounts</p>
                </div>
                <div className="p-3 bg-cyber-bg/70 border border-cyber-border/40 rounded-lg text-center">
                  <p className="text-[10px] text-gray-500 uppercase tracking-wider font-bold">Price</p>
                  <p className="text-xl font-black text-yellow-400 mt-1">₹{parseFloat(selectedProduct.price).toFixed(2)}</p>
                  <p className="text-[10px] text-gray-600 mt-0.5">{selectedProduct.category}</p>
                </div>
              </div>
            )}

            {/* Stock Added */}
            <div>
              <label className="block text-[10px] uppercase tracking-wider text-gray-400 font-bold mb-1.5">
                New Stock Added (count)
              </label>
              <input
                type="number"
                min="1"
                value={stockAdded || ''}
                onChange={(e) => setStockAdded(parseInt(e.target.value) || 0)}
                placeholder="e.g. 10"
                className="w-full px-4 py-2.5 bg-cyber-bg border border-cyber-border rounded-lg text-cyber-text placeholder-gray-600 focus:outline-none focus:border-yellow-400"
              />
            </div>

            {/* Custom Message (optional) */}
            <div>
              <label className="block text-[10px] uppercase tracking-wider text-gray-400 font-bold mb-1.5">
                Custom Message <span className="text-gray-600">(optional)</span>
              </label>
              <textarea
                rows={2}
                value={customMessage}
                onChange={(e) => setCustomMessage(e.target.value)}
                placeholder="e.g. Limited time offer! First come first serve..."
                className="w-full px-4 py-2.5 bg-cyber-bg border border-cyber-border rounded-lg text-cyber-text placeholder-gray-600 focus:outline-none focus:border-yellow-400 resize-none"
              />
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowPreview(!showPreview)}
                className="w-1/2 py-2.5 bg-cyber-bg border border-cyan-500/30 hover:border-cyan-500/60 text-cyan-400 rounded-lg font-bold uppercase tracking-widest transition-all active:scale-[0.98] flex items-center justify-center gap-2"
              >
                <Eye className="w-4 h-4" />
                {showPreview ? 'Hide' : 'Preview'}
              </button>
              <button
                type="button"
                onClick={handleSendBroadcast}
                disabled={sending || !selectedProductId || stockAdded <= 0}
                className="w-1/2 py-2.5 bg-gradient-to-r from-yellow-600 to-teal-600 hover:from-yellow-500 hover:to-teal-500 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-lg font-bold uppercase tracking-widest transition-all shadow-glow-yellow active:scale-[0.98] flex items-center justify-center gap-2"
              >
                {sending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Sending...
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    Broadcast
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* RIGHT: Preview Panel */}
        <div className="glass-panel p-6 rounded-xl border border-cyber-border/80 space-y-4">
          <div className="flex items-center gap-2 border-b border-cyber-border/40 pb-3">
            <Sparkles className="w-4 h-4 text-yellow-400" />
            <h2 className={`${headingStyle} text-lg`}>Message Preview</h2>
          </div>

          {selectedProduct && stockAdded > 0 ? (
            <div className="bg-[#1b2838] rounded-xl p-5 border border-gray-700/50 shadow-lg">
              {/* Simulated Telegram message */}
              <div className="space-y-3 text-sm text-white font-sans">
                <p className="font-bold text-center">🔔 <b>NEW STOCK ALERT!</b> 🔔</p>
                <p className="text-gray-500 text-center text-xs">▬▬▬▬▬▬▬▬▬▬▬</p>
                <div className="space-y-1.5 text-[13px]">
                  <p>{getProductEmoji(selectedProduct.name)} <b>Product:</b> {selectedProduct.name}</p>
                  <p>🗂️ <b>Category:</b> {selectedProduct.category}</p>
                  <p>💰 <b>Price:</b> ₹{parseFloat(selectedProduct.price).toFixed(2)}</p>
                </div>
                <div className="space-y-1.5 text-[13px] pt-1">
                  <p>📦 <b>Stock Added:</b> {stockAdded} accounts</p>
                  <p>📊 <b>Total Available:</b> {totalStock} accounts</p>
                </div>
                {customMessage && (
                  <p className="text-[13px] pt-1">💬 {customMessage}</p>
                )}
                <p className="text-gray-500 text-center text-xs">▬▬▬▬▬▬▬▬▬▬▬</p>
                <p className="text-[13px] italic text-gray-300">🛒 Grab yours before it&apos;s gone!</p>
                
                {/* Simulated inline buttons */}
                <div className="space-y-2 pt-3">
                  <div className="w-full py-2.5 bg-[#2d4059] hover:bg-[#3d5069] border border-gray-600/50 rounded-lg text-center text-xs font-medium text-blue-300 cursor-default transition-colors">
                    🛒 Buy {selectedProduct.name} Now
                  </div>
                  <div className="w-full py-2.5 bg-[#2d4059] hover:bg-[#3d5069] border border-gray-600/50 rounded-lg text-center text-xs font-medium text-blue-300 cursor-default transition-colors">
                    🛍️ Browse All Products
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-16 text-gray-500">
              <Package className="w-12 h-12 mb-3 text-gray-600" />
              <p className="text-xs font-sfpro uppercase tracking-widest">Select a product & enter stock count</p>
              <p className="text-[10px] text-gray-600 mt-1">to preview the broadcast message</p>
            </div>
          )}

          {/* Broadcast Info */}
          <div className="mt-4 p-3 bg-yellow-950/20 border border-yellow-500/10 rounded-lg">
            <p className="text-[10px] text-yellow-400/80 font-sfpro uppercase tracking-wider font-bold mb-1">ℹ️ Broadcast Info</p>
            <ul className="text-[11px] text-gray-400 font-sfpro space-y-1">
              <li>• This message will be sent to <b className="text-white">{totalUsers}</b> registered users</li>
              <li>• Messages are sent in background to avoid timeouts</li>
              <li>• Users get a <b className="text-cyan-400">Buy Now</b> button linking directly to the product</li>
              <li>• Broadcast is rate-limited to prevent Telegram API bans</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
