"use client"

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '../lib/supabaseClient'
import { Store, Lock, User, Terminal } from 'lucide-react'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // Custom design typography styles
  const headingStyle = "font-playfair font-black tracking-widest text-transparent bg-clip-text bg-gradient-to-r from-yellow-400 via-amber-500 to-orange-500"
  
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    
    try {
      const { data, error: authError } = await supabase.auth.signInWithPassword({
        email,
        password
      })
      
      if (authError) {
        throw new Error(authError.message)
      }
      
      router.push('/dashboard')
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Please verify credentials.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-cyber-bg flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background Matrix/Cyber grid effect */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#0c0e12_1px,transparent_1px),linear-gradient(to_bottom,#0c0e12_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_70%,transparent_100%)] opacity-30"></div>
      
      {/* Glowing elements */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-yellow-500/10 rounded-full blur-[120px] pointer-events-none"></div>
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-emerald-500/10 rounded-full blur-[120px] pointer-events-none"></div>

      {/* Main glass card panel */}
      <div className="w-full max-w-md glass-panel p-8 rounded-2xl glow-border-cyan relative z-10 shadow-glass">
        {/* Nexus Store Premium Logo */}
        <div className="flex flex-col items-center justify-center mb-6">
          <div className="w-16 h-16 rounded-full bg-cyber-fbi border border-yellow-500/30 flex items-center justify-center shadow-glow-yellow mb-3">
            <Store className="w-8 h-8 text-yellow-400 animate-pulse" />
          </div>
          <h2 className="text-xs uppercase tracking-[0.25em] text-yellow-400 font-bold font-sfpro">Nexus Store</h2>
          <h1 className={`${headingStyle} text-3xl mt-1 text-center`}>
            ADMIN CONTROL
          </h1>
          <p className="text-[10px] text-gray-500 uppercase tracking-widest mt-2 font-sfpro">Store Management Portal</p>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-950/50 border border-red-500/30 rounded-lg text-red-400 text-xs flex items-center gap-2 shadow-glow-red">
            <Terminal className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-[11px] uppercase tracking-wider text-gray-400 font-bold mb-1 font-sfpro">Admin Email Address</label>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <User className="h-4 w-4 text-yellow-500/40" />
              </span>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Enter email address"
                autoComplete="off"
                className="w-full pl-10 pr-4 py-2.5 bg-cyber-bg/80 border border-cyber-border rounded-lg text-xs text-cyber-text placeholder-gray-600 focus:outline-none focus:border-yellow-400 focus:ring-1 focus:ring-yellow-400 transition-all font-sfpro"
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] uppercase tracking-wider text-gray-400 font-bold mb-1 font-sfpro">Admin Password</label>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Lock className="h-4 w-4 text-yellow-500/40" />
              </span>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                autoComplete="new-password"
                className="w-full pl-10 pr-4 py-2.5 bg-cyber-bg/80 border border-cyber-border rounded-lg text-xs text-cyber-text placeholder-gray-600 focus:outline-none focus:border-yellow-400 focus:ring-1 focus:ring-yellow-400 transition-all font-sfpro"
              />
            </div>
          </div>

          <div className="pt-2">
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-gradient-to-r from-yellow-600 to-teal-600 hover:from-yellow-500 hover:to-teal-500 text-white font-bold rounded-lg text-xs tracking-widest uppercase transition-all shadow-glow-yellow hover:shadow-yellow-500/25 active:scale-[0.98] disabled:opacity-50 flex items-center justify-center gap-2 font-sfpro"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <>
                  <Store className="w-4 h-4" />
                  <span>Access Dashboard</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </main>
  )
}
