"use client"

import { useEffect, useState } from 'react'
import { supabase } from '../../../lib/supabaseClient'
import { MessageSquareHeart, Star, UserCircle, Calendar, ShieldCheck, Trash2 } from 'lucide-react'

type Review = {
  id: string
  telegram_id: number
  username: string
  first_name: string
  review_text: string
  created_at: string
}

export default function ReviewsPage() {
  const [reviews, setReviews] = useState<Review[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchReviews()

    // Real-time updates
    const subscription = supabase
      .channel('reviews-changes')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'reviews' }, () => {
        fetchReviews()
      })
      .subscribe()

    return () => {
      supabase.removeChannel(subscription)
    }
  }, [])

  const fetchReviews = async () => {
    try {
      const { data, error } = await supabase
        .from('reviews')
        .select('*')
        .order('created_at', { ascending: false })

      if (error) throw error
      setReviews(data || [])
    } catch (error) {
      console.error('Error fetching reviews:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteReview = async (id: string) => {
    if (!window.confirm("Are you sure you want to permanently delete this review?")) return;
    try {
      const { error } = await supabase.from('reviews').delete().eq('id', id);
      if (error) throw error;
      fetchReviews();
    } catch (err: any) {
      alert("Failed to delete review: " + err.message);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b border-cyber-border/30 pb-4">
        <div>
          <h1 className="text-2xl font-black font-playfair tracking-wide text-white drop-shadow-glow-yellow mb-1 flex items-center gap-3">
            <MessageSquareHeart className="text-yellow-400 w-8 h-8" />
            CUSTOMER REVIEWS
          </h1>
          <p className="text-xs text-gray-400 font-sfpro tracking-wider uppercase">Monitor customer feedback and testimonials</p>
        </div>
        <div className="px-4 py-2 bg-yellow-950/20 border border-yellow-500/30 rounded-lg flex flex-col items-end shadow-glow-yellow/5">
          <span className="text-[10px] text-yellow-500/80 font-bold uppercase tracking-widest font-sfpro">Total Reviews</span>
          <span className="text-lg font-black text-yellow-400">{reviews.length}</span>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center p-12">
          <div className="w-10 h-10 border-4 border-yellow-500 border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : reviews.length === 0 ? (
        <div className="p-12 text-center bg-cyber-card/40 border border-cyber-border rounded-xl">
          <MessageSquareHeart className="w-16 h-16 text-gray-600 mx-auto mb-4 opacity-50" />
          <h3 className="text-lg font-bold text-gray-300 font-playfair mb-2">No Reviews Yet</h3>
          <p className="text-sm text-gray-500 font-sfpro">Customer feedback will appear here once submitted via the Telegram bot.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {reviews.map((review) => (
            <div key={review.id} className="bg-cyber-card/60 backdrop-blur-md border border-cyber-border rounded-xl p-6 relative group overflow-hidden transition-all hover:border-yellow-500/30 hover:shadow-glow-yellow/5">
              {/* Decorative corner accent */}
              <div className="absolute top-0 right-0 w-16 h-16 bg-gradient-to-br from-yellow-500/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity rounded-bl-3xl"></div>
              
              <div className="flex justify-between items-start mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-cyber-bg border border-cyber-border flex items-center justify-center">
                    <UserCircle className="w-6 h-6 text-yellow-500" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white font-sfpro">{review.first_name || 'Anonymous User'}</h3>
                    <p className="text-[10px] text-gray-400 font-mono tracking-wider">@{review.username || review.telegram_id}</p>
                  </div>
                </div>
                <div className="flex">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <Star key={star} className="w-3.5 h-3.5 text-yellow-500 fill-yellow-500" />
                  ))}
                  <button 
                    onClick={() => handleDeleteReview(review.id)}
                    className="ml-3 p-1 rounded-md text-red-500/50 hover:bg-red-500/10 hover:text-red-400 transition-colors z-20 relative"
                    title="Delete Review"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
              
              <div className="mb-4 relative">
                <div className="absolute -left-2 -top-2 text-3xl text-cyber-border/40 font-serif leading-none">"</div>
                <p className="text-sm text-gray-300 leading-relaxed font-poppins relative z-10 italic pl-3">
                  {review.review_text}
                </p>
              </div>
              
              <div className="flex items-center justify-between pt-4 border-t border-cyber-border/50 text-[10px] text-gray-500 font-sfpro">
                <div className="flex items-center gap-1.5">
                  <Calendar className="w-3 h-3 text-gray-400" />
                  {new Date(review.created_at).toLocaleDateString(undefined, { 
                    year: 'numeric', month: 'short', day: 'numeric' 
                  })}
                </div>
                <div className="flex items-center gap-1.5 text-emerald-500/80 bg-emerald-950/20 px-2 py-0.5 rounded border border-emerald-500/20">
                  <ShieldCheck className="w-3 h-3" />
                  <span>Verified Purchase</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
