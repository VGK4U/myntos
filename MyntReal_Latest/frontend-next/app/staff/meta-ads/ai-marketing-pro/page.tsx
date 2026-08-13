"use client";

import { useState } from "react";

export default function AIMarketingProPage() {
  const [activeTab, setActiveTab] = useState("copy");
  const [generating, setGenerating] = useState(false);
  const [generatedContent, setGeneratedContent] = useState("");

  const handleGenerate = () => {
    setGenerating(true);
    setTimeout(() => {
      setGeneratedContent(
        "🚀 Discover Your Dream Home in Hyderabad!\n\nAre you looking for the perfect blend of luxury and convenience? MyntReal presents an exclusive collection of premium apartments located in the heart of the city.\n\n✨ Why Choose Us?\n- 24/7 Security & Gated Community\n- Resort-style Amenities\n- Proximity to Top Schools & IT Hubs\n\nDon't miss out on this opportunity. Click the link below to schedule a free site visit today! 👇\n[Link to landing page]"
      );
      setGenerating(false);
    }, 1500);
  };

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-6xl">
      <div className="flex justify-between items-end">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white shadow-md shadow-indigo-500/20">
              <i className="fas fa-brain text-xl"></i>
            </div>
            <h1 className="text-2xl font-extrabold text-gray-900 tracking-tight">AI Marketing Pro</h1>
          </div>
          <p className="text-gray-500">Supercharge your Meta Ads with AI-generated copy, audience predictions, and ROI forecasting.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sidebar Controls */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="p-4 border-b border-gray-100 bg-gray-50/50">
              <h3 className="font-bold text-gray-900"><i className="fas fa-magic text-indigo-500 mr-2"></i> AI Tools</h3>
            </div>
            <div className="p-2 flex flex-col gap-1">
              <button 
                onClick={() => setActiveTab("copy")}
                className={`w-full text-left px-4 py-3 rounded-lg text-sm font-medium transition-colors flex items-center justify-between ${
                  activeTab === "copy" 
                    ? "bg-indigo-50 text-indigo-700 border border-indigo-100" 
                    : "text-gray-600 hover:bg-gray-50"
                }`}
              >
                <span><i className="fas fa-pen-nib w-5"></i> Ad Copy Generator</span>
                {activeTab === "copy" && <i className="fas fa-chevron-right text-xs"></i>}
              </button>
              <button 
                onClick={() => setActiveTab("audience")}
                className={`w-full text-left px-4 py-3 rounded-lg text-sm font-medium transition-colors flex items-center justify-between ${
                  activeTab === "audience" 
                    ? "bg-indigo-50 text-indigo-700 border border-indigo-100" 
                    : "text-gray-600 hover:bg-gray-50"
                }`}
              >
                <span><i className="fas fa-users-viewfinder w-5"></i> Audience Targeting</span>
                {activeTab === "audience" && <i className="fas fa-chevron-right text-xs"></i>}
              </button>
              <button 
                onClick={() => setActiveTab("roi")}
                className={`w-full text-left px-4 py-3 rounded-lg text-sm font-medium transition-colors flex items-center justify-between ${
                  activeTab === "roi" 
                    ? "bg-indigo-50 text-indigo-700 border border-indigo-100" 
                    : "text-gray-600 hover:bg-gray-50"
                }`}
              >
                <span><i className="fas fa-chart-line w-5"></i> ROI Predictor</span>
                {activeTab === "roi" && <i className="fas fa-chevron-right text-xs"></i>}
              </button>
            </div>
          </div>

          {activeTab === "copy" && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
              <h3 className="font-bold text-gray-900 mb-4">Generation Parameters</h3>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Product / Service</label>
                  <select className="w-full text-sm border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500">
                    <option>Real Estate (Flats)</option>
                    <option>Real Estate (Plots)</option>
                    <option>Solar Solutions</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Target Persona</label>
                  <select className="w-full text-sm border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500">
                    <option>First-time Homebuyers</option>
                    <option>Investors</option>
                    <option>Retirees</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Tone of Voice</label>
                  <div className="flex gap-2">
                    <button className="flex-1 py-1.5 border border-indigo-500 bg-indigo-50 text-indigo-700 rounded text-xs font-medium">Professional</button>
                    <button className="flex-1 py-1.5 border border-gray-200 bg-white text-gray-600 rounded text-xs font-medium hover:bg-gray-50">Urgent</button>
                    <button className="flex-1 py-1.5 border border-gray-200 bg-white text-gray-600 rounded text-xs font-medium hover:bg-gray-50">Friendly</button>
                  </div>
                </div>

                <button 
                  onClick={handleGenerate}
                  disabled={generating}
                  className="w-full py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white font-bold rounded-lg shadow-sm transition-all text-sm disabled:opacity-70 mt-2"
                >
                  {generating ? (
                    <span className="flex items-center justify-center gap-2"><i className="fas fa-spinner fa-spin"></i> Generating...</span>
                  ) : (
                    <span className="flex items-center justify-center gap-2"><i className="fas fa-sparkles"></i> Generate Ad Copy</span>
                  )}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Main Display Area */}
        <div className="lg:col-span-2">
          {activeTab === "copy" && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 h-full flex flex-col">
              <div className="p-4 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
                <h3 className="font-bold text-gray-900">AI Generated Copy</h3>
                <div className="flex gap-2">
                  <button className="px-3 py-1.5 text-xs font-medium text-gray-600 bg-white border border-gray-200 rounded hover:bg-gray-50 transition-colors">
                    <i className="fas fa-copy mr-1"></i> Copy
                  </button>
                  <button className="px-3 py-1.5 text-xs font-medium text-white bg-indigo-600 rounded hover:bg-indigo-700 transition-colors">
                    <i className="fas fa-paper-plane mr-1"></i> Send to Meta
                  </button>
                </div>
              </div>
              <div className="p-6 flex-1 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]">
                {generatedContent ? (
                  <div className="bg-white p-6 rounded-lg border border-indigo-100 shadow-sm relative animate-in zoom-in-95 duration-300">
                    <div className="absolute -top-3 -right-3 w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center border-2 border-white">
                      <i className="fas fa-sparkles text-indigo-600 text-xs"></i>
                    </div>
                    <pre className="whitespace-pre-wrap font-sans text-gray-800 text-sm leading-relaxed">
                      {generatedContent}
                    </pre>
                  </div>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-gray-400">
                    <i className="fas fa-pen-fancy text-4xl mb-4 text-gray-300"></i>
                    <p>Select your parameters and click generate to create high-converting ad copy.</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === "audience" && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 h-full p-8 flex flex-col items-center justify-center text-center">
              <div className="w-16 h-16 bg-indigo-50 rounded-full flex items-center justify-center mb-4">
                <i className="fas fa-users-viewfinder text-2xl text-indigo-500"></i>
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-2">Audience Targeting Prediction</h3>
              <p className="text-gray-500 max-w-md mb-6">Connect your Meta Business account to allow the AI to analyze past campaign performance and suggest the optimal Lookalike Audiences.</p>
              <button className="px-6 py-2.5 bg-gray-900 text-white font-bold rounded-lg hover:bg-black transition-colors shadow-sm">
                Connect Meta Account
              </button>
            </div>
          )}

          {activeTab === "roi" && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 h-full p-8 flex flex-col items-center justify-center text-center">
              <div className="w-16 h-16 bg-emerald-50 rounded-full flex items-center justify-center mb-4">
                <i className="fas fa-chart-line text-2xl text-emerald-500"></i>
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-2">Campaign ROI Forecaster</h3>
              <p className="text-gray-500 max-w-md mb-6">Input your estimated budget and let our machine learning model predict your Cost Per Lead (CPL) and estimated conversions based on historical industry data.</p>
              <button className="px-6 py-2.5 bg-gray-900 text-white font-bold rounded-lg hover:bg-black transition-colors shadow-sm">
                Open Forecaster
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
