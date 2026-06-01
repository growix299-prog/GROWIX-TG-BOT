"use client"

import { useEffect, useState } from 'react'
import { supabase } from '../../../lib/supabaseClient'
import { ShoppingBag, Plus, Trash2, Edit2, Check, X, ShieldAlert, Layers, Download } from 'lucide-react'

export default function ProductsPage() {
  const [products, setProducts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingProduct, setEditingProduct] = useState<any | null>(null)
  
  // Form fields
  const [name, setName] = useState('')
  const [category, setCategory] = useState('Games')
  const [price, setPrice] = useState('')
  const [deliveryType, setDeliveryType] = useState('AUTO')
  const [active, setActive] = useState(true)
  
  const [formError, setFormError] = useState<string | null>(null)

  // Undo Delete states
  const [undoProduct, setUndoProduct] = useState<any | null>(null)
  const [undoSeconds, setUndoSeconds] = useState(5)
  const [activeTimer, setActiveTimer] = useState<any>(null)

  const fetchProducts = async () => {
    try {
      setLoading(true)
      const { data, error } = await supabase
        .from('products')
        .select('*')
        .order('created_at', { ascending: false })
      if (error) throw error
      setProducts(data || [])
    } catch (err: any) {
      console.error("Error loading products:", err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchProducts()
    return () => {
      if (activeTimer) clearInterval(activeTimer)
    }
  }, [])

  const DEFAULT_PRODUCTS = [
    { name: 'Netflix', category: 'OTT', price: 199, delivery_type: 'AUTO', active: true },
    { name: 'YouTube Premium', category: 'OTT', price: 99, delivery_type: 'AUTO', active: true },
    { name: 'Spotify Premium', category: 'OTT', price: 99, delivery_type: 'AUTO', active: true },
    { name: 'Amazon Prime', category: 'OTT', price: 99, delivery_type: 'AUTO', active: true },
    { name: 'Disney+ Hotstar', category: 'OTT', price: 149, delivery_type: 'AUTO', active: true },
    { name: 'Steam Account', category: 'Games', price: 299, delivery_type: 'AUTO', active: true },
    { name: 'Zee5', category: 'OTT', price: 79, delivery_type: 'AUTO', active: true },
    { name: 'Sony Liv', category: 'OTT', price: 89, delivery_type: 'AUTO', active: true },
    { name: 'ChatGPT Plus', category: 'AI', price: 499, delivery_type: 'AUTO', active: true },
    { name: 'CapCut Pro', category: 'VideoEditing', price: 149, delivery_type: 'AUTO', active: true },
    { name: 'Google One', category: 'AI', price: 199, delivery_type: 'AUTO', active: true },
    { name: 'Canva Pro', category: 'VideoEditing', price: 99, delivery_type: 'AUTO', active: true },
    { name: 'Crunchyroll', category: 'OTT', price: 99, delivery_type: 'AUTO', active: true },
    { name: 'Claude AI Pro', category: 'AI', price: 499, delivery_type: 'AUTO', active: true },
    { name: 'Adobe Creative Cloud', category: 'VideoEditing', price: 599, delivery_type: 'AUTO', active: true },
  ]

  const injectDefaults = async () => {
    try {
      setLoading(true)
      const { error } = await supabase.from('products').insert(DEFAULT_PRODUCTS)
      if (error) throw error
      fetchProducts()
    } catch (err: any) {
      alert("Error injecting defaults: " + err.message)
      setLoading(false)
    }
  }

  const openAddModal = () => {
    setEditingProduct(null)
    setName('')
    setCategory('Games')
    setPrice('')
    setDeliveryType('AUTO')
    setActive(true)
    setFormError(null)
    setIsModalOpen(true)
  }

  const openEditModal = (product: any) => {
    setEditingProduct(product)
    setName(product.name)
    setCategory(product.category)
    setPrice(String(product.price))
    setDeliveryType(product.delivery_type)
    setActive(product.active)
    setFormError(null)
    setIsModalOpen(true)
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)
    
    if (!name.trim()) {
      setFormError("Product name is required.")
      return
    }
    const numPrice = Number(price)
    if (isNaN(numPrice) || numPrice < 0) {
      setFormError("Please enter a valid positive price.")
      return
    }

    const payload = {
      name,
      category,
      price: numPrice,
      delivery_type: deliveryType,
      active
    }

    try {
      if (editingProduct) {
        // Update operation
        const { error } = await supabase
          .from('products')
          .update(payload)
          .eq('id', editingProduct.id)
        if (error) throw error
      } else {
        // Insert operation
        const { error } = await supabase
          .from('products')
          .insert([payload])
        if (error) throw error
      }
      setIsModalOpen(false)
      fetchProducts()
    } catch (err: any) {
      setFormError(err.message)
    }
  }

  // Soft delete with 5s countdown
  const startSoftDelete = (product: any) => {
    // If there is already a pending delete, commit it instantly first
    if (undoProduct) {
      commitDelete(undoProduct.id)
    }

    // Capture the target product and remove it from UI array immediately
    setUndoProduct(product)
    setProducts((prev) => prev.filter((p) => p.id !== product.id))
    setUndoSeconds(5)

    // Clear any active timer just in case
    if (activeTimer) clearInterval(activeTimer)

    let secondsLeft = 5
    const timer = setInterval(() => {
      secondsLeft -= 1
      setUndoSeconds(secondsLeft)
      if (secondsLeft <= 0) {
        clearInterval(timer)
        commitDelete(product.id)
      }
    }, 1000)

    setActiveTimer(timer)
  }

  // Restore item if user clicks undo
  const triggerUndo = () => {
    if (activeTimer) clearInterval(activeTimer)
    if (undoProduct) {
      // Put it back at its original index or list
      setProducts((prev) => [undoProduct, ...prev])
      setUndoProduct(null)
      setActiveTimer(null)
    }
  }

  // Permanent Delete call
  const commitDelete = async (id: string) => {
    try {
      const { error } = await supabase
        .from('products')
        .delete()
        .eq('id', id)
      if (error) {
        if (error.message.includes('foreign key constraint')) {
            alert("Delete Failed: This product is linked to Orders or Credentials! Please delete its related accounts/orders first.");
        } else {
            alert("Delete failed: " + error.message);
        }
        throw error;
      }
      fetchProducts();
    } catch (err: any) {
      console.error("Delete failed: ", err.message)
    } finally {
      setUndoProduct(null)
      setActiveTimer(null)
    }
  }

  const toggleActive = async (product: any) => {
    try {
      const { error } = await supabase
        .from('products')
        .update({ active: !product.active })
        .eq('id', product.id)
      if (error) throw error
      fetchProducts()
    } catch (err: any) {
      console.error(err.message)
    }
  }

  const headingStyle = "font-playfair font-black tracking-wide text-white"

  return (
    <div className="space-y-8">
      {/* Header operations */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className={`${headingStyle} text-3xl`}>Catalog Manager</h1>
          <p className="text-xs text-gray-500 font-sfpro mt-1 uppercase tracking-widest">Create, modify, and monitor active products</p>
        </div>
        <div className="flex items-center gap-3">
          {products.length === 0 && !loading && (
            <button
              onClick={injectDefaults}
              className="flex items-center gap-2 px-5 py-2.5 bg-cyan-900/60 hover:bg-cyan-800 text-cyan-400 border border-cyan-500/30 rounded-lg text-xs font-bold uppercase tracking-widest transition-all font-sfpro active:scale-[0.98]"
            >
              <Download className="w-4.5 h-4.5" />
              <span>Load Default List</span>
            </button>
          )}
          <button
            onClick={openAddModal}
            className="flex items-center gap-2 px-5 py-2.5 bg-yellow-600 hover:bg-yellow-500 text-white rounded-lg text-xs font-bold uppercase tracking-widest shadow-glow-yellow transition-all font-sfpro active:scale-[0.98]"
          >
            <Plus className="w-4.5 h-4.5" />
            <span>Deploy Product</span>
          </button>
        </div>
      </div>

      {loading ? (
        <div className="h-96 flex items-center justify-center">
          <div className="w-8 h-8 border-2 border-yellow-500 border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : (
        <div className="space-y-12">
          {products.length === 0 ? (
            <div className="col-span-full glass-panel py-16 text-center text-gray-500 uppercase tracking-widest text-xs font-sfpro border border-cyber-border rounded-xl">
              <ShoppingBag className="w-12 h-12 mx-auto mb-4 text-gray-600 animate-pulse" />
              <span>Catalog Empty. Create products or load defaults to start!</span>
            </div>
          ) : (
            ['OTT', 'Games', 'AI', 'VideoEditing'].map((cat) => {
              const catProducts = products.filter(p => p.category === cat);
              return (
                <div key={cat} className="space-y-4">
                  <div className="flex items-center justify-between border-b border-cyber-border/40 pb-2">
                    <h2 className="text-xl font-bold text-white tracking-wider font-playfair uppercase">
                      {cat === 'VideoEditing' ? 'VIDEO EDITING' : cat}
                    </h2>
                    <button
                      onClick={() => {
                        setEditingProduct(null)
                        setName('')
                        setCategory(cat)
                        setPrice('')
                        setDeliveryType('AUTO')
                        setActive(true)
                        setFormError(null)
                        setIsModalOpen(true)
                      }}
                      className="text-[10px] text-yellow-500 hover:text-yellow-400 font-bold uppercase tracking-widest flex items-center gap-1 transition-all"
                    >
                      <Plus className="w-3.5 h-3.5" /> Add New
                    </button>
                  </div>

                  {catProducts.length === 0 ? (
                    <div className="text-gray-600 text-xs py-6 text-center border border-dashed border-cyber-border/30 rounded-lg font-sfpro uppercase tracking-widest">
                      No active {cat} items
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                      {catProducts.map((prod) => (
                        <div 
                          key={prod.id} 
                          className={`glass-panel p-6 rounded-xl relative transition-all overflow-hidden flex flex-col justify-between h-48 border ${
                            prod.active ? 'border-cyber-border/80 hover:border-yellow-500/50 hover:shadow-glow-yellow/5' : 'border-red-950/40 opacity-60'
                          }`}
                        >
                          <div>
                            <div className="flex items-center justify-between mb-3">
                              <span className={`px-2 py-0.5 rounded text-[9px] font-black font-sfpro uppercase ${
                                prod.category === 'OTT' 
                                  ? 'bg-purple-950/80 text-purple-400 border border-purple-500/20' 
                                  : prod.category === 'AI'
                                  ? 'bg-blue-950/80 text-blue-400 border border-blue-500/20'
                                  : prod.category === 'VideoEditing'
                                  ? 'bg-pink-950/80 text-pink-400 border border-pink-500/20'
                                  : 'bg-yellow-950/80 text-yellow-400 border border-yellow-500/20'
                              }`}>
                                {prod.category === 'VideoEditing' ? 'VIDEO EDITING' : prod.category}
                              </span>
                              <span className="text-lg font-black font-sfpro text-emerald-400">
                                ₹{parseFloat(prod.price).toFixed(2)}
                              </span>
                            </div>
                            <h3 className="text-base font-bold text-white tracking-wide truncate mb-1">{prod.name}</h3>
                            <p className="text-[10px] text-gray-500 font-sfpro uppercase tracking-wider flex items-center gap-1.5">
                              <Layers className="w-3.5 h-3.5 text-gray-500" />
                              <span>Delivery: {prod.delivery_type === 'AUTO' ? 'Auto-Credential Dispatch' : 'Manual Setup Email'}</span>
                            </p>
                          </div>

                          <div className="flex items-center justify-between pt-4 border-t border-cyber-border/30 mt-4">
                            <button
                              onClick={() => toggleActive(prod)}
                              className={`flex items-center gap-1.5 px-3 py-1 rounded text-[10px] font-bold tracking-wider uppercase font-sfpro transition-all ${
                                prod.active 
                                  ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-950' 
                                  : 'bg-red-950/60 text-red-400 border border-red-500/20 hover:bg-red-950'
                              }`}
                            >
                              {prod.active ? <Check className="w-3.5 h-3.5" /> : <X className="w-3.5 h-3.5" />}
                              <span>{prod.active ? 'Active' : 'Offline'}</span>
                            </button>

                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => openEditModal(prod)}
                                className="p-2 bg-cyber-bg hover:bg-yellow-950/30 text-gray-400 hover:text-yellow-400 border border-cyber-border rounded-lg transition-all"
                              >
                                <Edit2 className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => startSoftDelete(prod)}
                                className="p-2 bg-cyber-bg hover:bg-red-950/30 text-gray-400 hover:text-red-400 border border-cyber-border rounded-lg transition-all"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )
            })
          )}
        </div>
      )}

      {/* CRUD Add/Edit Product Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 pl-64 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="w-full max-w-md glass-panel p-8 rounded-2xl glow-border-cyan shadow-glass relative">
            <h2 className={`${headingStyle} text-xl mb-6`}>
              {editingProduct ? 'Configure Product Parameters' : 'Deploy New Catalog Item'}
            </h2>

            {formError && (
              <div className="mb-4 p-3 bg-red-950/50 border border-red-500/30 rounded-lg text-red-400 text-xs flex items-center gap-2 font-sfpro">
                <ShieldAlert className="w-4.5 h-4.5 flex-shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleSave} className="space-y-5 text-xs font-sfpro">
              <div>
                <label className="block text-[10px] uppercase tracking-wider text-gray-400 font-bold mb-1">Product Title</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g., Netflix Premium Ultra HD"
                  className="w-full px-4 py-2.5 bg-cyber-bg border border-cyber-border rounded-lg text-cyber-text placeholder-gray-600 focus:outline-none focus:border-yellow-400"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[10px] uppercase tracking-wider text-gray-400 font-bold mb-1">Category</label>
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className="w-full px-4 py-2.5 bg-cyber-bg border border-cyber-border rounded-lg text-cyber-text focus:outline-none focus:border-yellow-400"
                  >
                    <option value="Games">Games</option>
                    <option value="OTT">OTT</option>
                    <option value="AI">AI Subscriptions</option>
                    <option value="VideoEditing">Video Editing</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] uppercase tracking-wider text-gray-400 font-bold mb-1">Price (INR)</label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    value={price}
                    onChange={(e) => setPrice(e.target.value)}
                    placeholder="199.00"
                    className="w-full px-4 py-2.5 bg-cyber-bg border border-cyber-border rounded-lg text-cyber-text placeholder-gray-600 focus:outline-none focus:border-yellow-400"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[10px] uppercase tracking-wider text-gray-400 font-bold mb-1">Delivery Protocol</label>
                <select
                  value={deliveryType}
                  onChange={(e) => setDeliveryType(e.target.value)}
                  className="w-full px-4 py-2.5 bg-cyber-bg border border-cyber-border rounded-lg text-cyber-text focus:outline-none focus:border-yellow-400"
                >
                  <option value="AUTO">AUTO (Auto-deliver credentials)</option>
                </select>
              </div>

              <div className="flex items-center gap-3 pt-2">
                <input
                  type="checkbox"
                  id="active"
                  checked={active}
                  onChange={(e) => setActive(e.target.checked)}
                  className="w-4 h-4 rounded bg-cyber-bg border-cyber-border text-yellow-500 focus:ring-transparent"
                />
                <label htmlFor="active" className="text-[11px] font-bold uppercase tracking-wider text-gray-300 cursor-pointer">
                  Activate and list immediately in bot
                </label>
              </div>

              <div className="flex gap-3 pt-4 border-t border-cyber-border/40">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="w-1/2 py-2.5 bg-cyber-bg border border-cyber-border hover:bg-cyber-card text-gray-400 rounded-lg font-bold uppercase tracking-widest active:scale-[0.98] transition-all"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="w-1/2 py-2.5 bg-yellow-600 hover:bg-yellow-500 text-white rounded-lg font-bold uppercase tracking-widest shadow-glow-yellow active:scale-[0.98] transition-all"
                >
                  Confirm Item
                </button>
              </div>
            </form>

          </div>
        </div>
      )}

      {/* 5-Second Undo Toast */}
      {undoProduct && (
        <div className="fixed bottom-6 right-6 z-50 glass-panel px-6 py-4 rounded-xl border border-rose-500/30 shadow-glow-rose/10 flex items-center justify-between gap-6 animate-slide-up">
          <div className="flex items-center gap-3">
            <span className="h-2 w-2 rounded-full bg-rose-500 animate-ping"></span>
            <div className="text-xs font-sfpro">
              <p className="text-white font-bold">Deleted "{undoProduct.name}"</p>
              <p className="text-gray-400 text-[10px]">Permanent delete in <span className="text-rose-400 font-bold">{undoSeconds}s</span></p>
            </div>
          </div>
          <button
            onClick={triggerUndo}
            className="px-3 py-1 bg-yellow-950 border border-yellow-500/30 text-yellow-400 hover:text-cyan-300 font-bold uppercase text-[10px] tracking-wider rounded-lg transition-all active:scale-95"
          >
            Undo Delete
          </button>
        </div>
      )}
    </div>
  )
}
