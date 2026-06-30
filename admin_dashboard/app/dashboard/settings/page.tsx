"use client"

import { useState } from 'react'
import { supabase } from '../../../lib/supabaseClient'
import { Settings, Lock, Mail, ShieldAlert, CheckCircle2 } from 'lucide-react'

export default function SettingsPage() {
  const [newEmail, setNewEmail] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  
  const [emailLoading, setEmailLoading] = useState(false)
  const [passwordLoading, setPasswordLoading] = useState(false)
  
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  const handleUpdateEmail = async (e: React.FormEvent) => {
    e.preventDefault()
    setEmailLoading(true)
    setMessage(null)
    
    try {
      const { error } = await supabase.auth.updateUser({ email: newEmail })
      if (error) throw error
      
      setMessage({ type: 'success', text: 'Email update initiated. Please check your new email for a confirmation link.' })
      setNewEmail('')
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to update email.' })
    } finally {
      setEmailLoading(false)
    }
  }

  const handleUpdatePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (newPassword !== confirmPassword) {
      setMessage({ type: 'error', text: 'Passwords do not match.' })
      return
    }
    
    if (newPassword.length < 6) {
      setMessage({ type: 'error', text: 'Password must be at least 6 characters.' })
      return
    }

    setPasswordLoading(true)
    setMessage(null)
    
    try {
      const { error } = await supabase.auth.updateUser({ password: newPassword })
      if (error) throw error
      
      setMessage({ type: 'success', text: 'Password successfully updated.' })
      setNewPassword('')
      setConfirmPassword('')
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to update password.' })
    } finally {
      setPasswordLoading(false)
    }
  }

  return (
    <div className="max-w-4xl space-y-6">
      <div className="flex items-center gap-3 mb-8">
        <div className="w-10 h-10 rounded-xl bg-yellow-950 border border-yellow-500/40 flex items-center justify-center shadow-glow-yellow">
          <Settings className="w-5 h-5 text-yellow-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold font-playfair tracking-wide text-white">Security Settings</h1>
          <p className="text-xs text-gray-400 font-sfpro mt-1">Manage your admin console credentials</p>
        </div>
      </div>

      {message && (
        <div className={`p-4 rounded-lg border flex items-center gap-3 text-sm font-sfpro ${
          message.type === 'success' 
            ? 'bg-emerald-950/30 border-emerald-500/30 text-emerald-400 shadow-glow-emerald/10' 
            : 'bg-red-950/30 border-red-500/30 text-red-400 shadow-glow-red/10'
        }`}>
          {message.type === 'success' ? <CheckCircle2 className="w-5 h-5 flex-shrink-0" /> : <ShieldAlert className="w-5 h-5 flex-shrink-0" />}
          <span>{message.text}</span>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Update Email Panel */}
        <div className="glass-panel p-6 rounded-xl border border-cyber-border glow-border-cyan">
          <h2 className="text-sm font-bold text-yellow-400 uppercase tracking-widest font-sfpro mb-4 flex items-center gap-2">
            <Mail className="w-4 h-4" />
            Update Email Address
          </h2>
          <p className="text-xs text-gray-400 mb-6 font-sfpro">
            Change the email address used to log into the admin dashboard. You will need to verify the new email address.
          </p>
          
          <form onSubmit={handleUpdateEmail} className="space-y-4">
            <div>
              <label className="block text-[11px] uppercase tracking-wider text-gray-400 font-bold mb-1 font-sfpro">New Email Address</label>
              <input
                type="email"
                required
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                placeholder="admin@example.com"
                className="w-full px-4 py-2.5 bg-cyber-bg border border-cyber-border rounded-lg text-sm text-cyber-text placeholder-gray-600 focus:outline-none focus:border-yellow-400 focus:ring-1 focus:ring-yellow-400 transition-all font-sfpro"
              />
            </div>
            
            <button
              type="submit"
              disabled={emailLoading || !newEmail}
              className="w-full py-2.5 bg-cyan-950/40 hover:bg-cyan-900/60 border border-cyan-500/30 hover:border-cyan-400/50 text-cyan-400 font-bold rounded-lg text-xs tracking-widest uppercase transition-all shadow-glow-cyan/10 disabled:opacity-50 flex items-center justify-center gap-2 font-sfpro"
            >
              {emailLoading ? (
                <div className="w-4 h-4 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin"></div>
              ) : (
                'Update Email'
              )}
            </button>
          </form>
        </div>

        {/* Update Password Panel */}
        <div className="glass-panel p-6 rounded-xl border border-cyber-border glow-border-cyan">
          <h2 className="text-sm font-bold text-yellow-400 uppercase tracking-widest font-sfpro mb-4 flex items-center gap-2">
            <Lock className="w-4 h-4" />
            Update Password
          </h2>
          <p className="text-xs text-gray-400 mb-6 font-sfpro">
            Ensure your account is using a long, random password to stay secure. Password must be at least 6 characters.
          </p>
          
          <form onSubmit={handleUpdatePassword} className="space-y-4">
            <div>
              <label className="block text-[11px] uppercase tracking-wider text-gray-400 font-bold mb-1 font-sfpro">New Password</label>
              <input
                type="password"
                required
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Enter new password"
                className="w-full px-4 py-2.5 bg-cyber-bg border border-cyber-border rounded-lg text-sm text-cyber-text placeholder-gray-600 focus:outline-none focus:border-yellow-400 focus:ring-1 focus:ring-yellow-400 transition-all font-sfpro"
              />
            </div>

            <div>
              <label className="block text-[11px] uppercase tracking-wider text-gray-400 font-bold mb-1 font-sfpro">Confirm New Password</label>
              <input
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter new password"
                className="w-full px-4 py-2.5 bg-cyber-bg border border-cyber-border rounded-lg text-sm text-cyber-text placeholder-gray-600 focus:outline-none focus:border-yellow-400 focus:ring-1 focus:ring-yellow-400 transition-all font-sfpro"
              />
            </div>
            
            <button
              type="submit"
              disabled={passwordLoading || !newPassword || !confirmPassword}
              className="w-full py-2.5 bg-yellow-950/40 hover:bg-yellow-900/60 border border-yellow-500/30 hover:border-yellow-400/50 text-yellow-400 font-bold rounded-lg text-xs tracking-widest uppercase transition-all shadow-glow-yellow/10 disabled:opacity-50 flex items-center justify-center gap-2 font-sfpro"
            >
              {passwordLoading ? (
                <div className="w-4 h-4 border-2 border-yellow-400 border-t-transparent rounded-full animate-spin"></div>
              ) : (
                'Change Password'
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
