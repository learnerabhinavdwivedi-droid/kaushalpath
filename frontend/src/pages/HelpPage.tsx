import React, { useState } from 'react';
import { Bot, Phone, Send, X, ChevronRight, ArrowLeft } from 'lucide-react';
import { createMentorRequest } from '../api/client';
import { BackgroundDoodles } from '../components/BackgroundDoodles';
import { Link } from 'wouter';

export const HelpPage: React.FC = () => {
  const [showMentorForm, setShowMentorForm] = useState(false);
  const [phone, setPhone] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [toastMessage, setToastMessage] = useState('');

  const faqs = [
    { question: "What is the Kaushal Path?", answer: "It's an AI-driven platform helping families make informed career choices." },
    { question: "How are recommendations made?", answer: "Based on your aptitudes, interests, and family constraints." },
    { question: "Need a mentor 🙋‍♂️", isAction: true },
    { question: "What if I want to change paths?", answer: "You can always retake the assessment or adjust constraints in the room." }
  ];

  const handleFAQClick = (faq: any) => {
    if (faq.isAction) {
      setShowMentorForm(true);
    } else {
      setToastMessage(`🤖 ${faq.answer}`);
      setTimeout(() => setToastMessage(''), 5000);
    }
  };

  const handleMentorSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!phone) return;
    setSubmitting(true);
    try {
      await createMentorRequest(phone);
      setShowMentorForm(false);
      setPhone('');
      setToastMessage("Awesome! Your mentor request is registered !! 🌟👩‍🏫 We will contact you soon!");
      setTimeout(() => setToastMessage(''), 8000);
    } catch (e: any) {
      alert(e.message || "Failed to submit request.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleBack = () => {
    if (window.history.length > 1) {
      window.history.back();
    } else {
      window.location.href = '/';
    }
  };

  return (
    <div className="relative min-h-screen bg-page overflow-hidden py-8 px-4 sm:px-6">
      <BackgroundDoodles section="help" />

      <div className="relative z-10 max-w-2xl mx-auto">
        {/* Navigation Header */}
        <div className="mb-6 flex items-center justify-between">
          <button
            onClick={handleBack}
            className="btn-secondary flex items-center gap-2 text-sm font-medium py-2 px-3 shadow-sm bg-white"
          >
            <ArrowLeft size={16} /> Back
          </button>
          <Link href="/" className="text-sm font-medium text-accent hover:underline">
            Home
          </Link>
        </div>

        {/* Main Content Card */}
        <div className="card flex flex-col items-center p-6 sm:p-8 space-y-6 relative overflow-hidden bg-gradient-to-br from-white to-blue-50/50 shadow-md">
          {/* Toast Notification */}
          {toastMessage && (
            <div className="w-full bg-white border-2 border-accent shadow-xl rounded-xl p-4 flex items-start gap-2 animate-float">
              <div className="flex-1">
                <p className="font-bold text-accent text-sm md:text-base">{toastMessage}</p>
              </div>
              <button onClick={() => setToastMessage('')} className="text-gray-400 hover:text-gray-600">
                <X size={18} />
              </button>
            </div>
          )}

          {/* Robot Avatar */}
          <div className="relative group pt-4">
            <div className="absolute inset-0 bg-accent/20 rounded-full blur-xl scale-150 group-hover:bg-accent/30 transition-all duration-500"></div>
            <div className="relative bg-white border-4 border-accent p-4 rounded-full shadow-lg animate-bounce">
              <Bot size={56} className="text-accent" />
            </div>
            {/* Speech Bubble */}
            <div className="absolute -top-3 -right-24 sm:-right-28 bg-white px-4 py-2 rounded-2xl rounded-bl-none shadow-md border border-gray-100 whitespace-nowrap animate-float">
              <p className="font-bold text-accent text-sm">Have any doubt, ask me! 🤖✨</p>
            </div>
          </div>

          <div className="w-full max-w-lg space-y-4 mt-2">
            <h1 className="font-bold text-2xl text-center text-ink">Frequently Asked Questions</h1>
            <p className="text-sm text-textSecondary text-center">
              Find instant answers to common vocational counselling questions or request a call from a human mentor.
            </p>

            {showMentorForm ? (
              <form onSubmit={handleMentorSubmit} className="bg-white p-6 rounded-2xl border-2 border-accent shadow-sm space-y-4">
                <h4 className="font-bold text-accent text-lg flex items-center gap-2">
                  <Phone size={20} /> Mentor Request
                </h4>
                <p className="text-sm text-textSecondary">
                  Please enter your phone number. Our expert mentor will reach out to you directly.
                </p>
                <input
                  type="tel"
                  placeholder="e.g. +91 9876543210"
                  className="input-field w-full text-base"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  required
                />
                <div className="flex gap-3 pt-2">
                  <button type="button" onClick={() => setShowMentorForm(false)} className="btn-secondary flex-1">
                    Cancel
                  </button>
                  <button type="submit" disabled={submitting} className="btn-primary flex-1 flex items-center justify-center gap-2">
                    {submitting ? 'Sending...' : 'Request'} <Send size={16} />
                  </button>
                </div>
              </form>
            ) : (
              <div className="space-y-3 pt-2">
                {faqs.map((faq, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleFAQClick(faq)}
                    className={`w-full flex items-center justify-between p-4 rounded-xl border text-left transition-all duration-200 ${
                      faq.isAction
                        ? 'border-orange bg-orange/5 hover:bg-orange/10 font-bold text-orange'
                        : 'border-gray-200 bg-white hover:border-accent/50 hover:bg-gray-50 text-ink shadow-sm'
                    }`}
                  >
                    <span className="font-medium">{faq.question}</span>
                    <ChevronRight size={20} className={faq.isAction ? 'text-orange' : 'text-gray-400'} />
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
