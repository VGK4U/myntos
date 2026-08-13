"use client";

import { useState } from "react";

type Tab = "all" | "events" | "offers" | "submit";

export default function AnnouncementsPage() {
  const [activeTab, setActiveTab] = useState<Tab>("all");
  const [searchId, setSearchId] = useState("");
  const [userData, setUserData] = useState<any>(null);

  const handleSearch = () => {
    if (!searchId.trim()) return;
    setUserData({
      name: "Anil Kumar", id: searchId.toUpperCase(), type: searchId.toUpperCase().startsWith('VGK') ? 'VGK Member' : 'MNR Member'
    });
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2 flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-sky-500/10 flex items-center justify-center">
              <i className="fas fa-bullhorn text-sky-600"></i>
            </div>
            User Announcements
          </h1>
          <p className="text-gray-500">
            Manage events, offers, and news broadcasts for members.
          </p>
        </div>
      </div>

      <div className="p-6 rounded-xl bg-white border border-gray-200 shadow-sm">
        <div className="flex flex-col md:flex-row gap-6 items-end">
          <div className="flex-1 w-full max-w-md">
            <label className="block text-sm font-bold text-gray-900 mb-2">Search Member (MNR or VGK)</label>
            <div className="flex gap-2">
              <input 
                type="text" 
                value={searchId}
                onChange={(e) => setSearchId(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                className="w-full bg-gray-50 border border-gray-200 rounded-lg py-2.5 px-4 text-gray-900 focus:outline-none focus:ring-2 focus:ring-sky-500/50 focus:border-sky-500 transition-all uppercase"
                placeholder="e.g. MNR10025"
              />
              <button 
                onClick={handleSearch}
                className="px-6 py-2.5 bg-gray-900 hover:bg-black text-white font-bold rounded-lg transition-colors flex items-center gap-2 shadow-sm"
              >
                <i className="fas fa-search"></i> Search
              </button>
            </div>
          </div>
          {userData && (
            <div className="flex-1">
              <div className="p-4 rounded-lg bg-sky-50 border border-sky-100 flex items-center gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-bold text-gray-900">{userData.name}</h3>
                    <span className="px-2 py-0.5 rounded text-xs font-medium bg-sky-100 text-sky-700 border border-sky-200">
                      {userData.type}
                    </span>
                  </div>
                  <div className="text-sm text-gray-500 mt-1">{userData.id}</div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {userData && (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
          <div className="flex border-b border-gray-200 mb-6 bg-white px-2 rounded-t-xl overflow-hidden shadow-sm">
            <TabButton active={activeTab === 'all'} onClick={() => setActiveTab('all')} label="All Announcements" />
            <TabButton active={activeTab === 'events'} onClick={() => setActiveTab('events')} label="Events" />
            <TabButton active={activeTab === 'offers'} onClick={() => setActiveTab('offers')} label="Offers" />
            <div className="flex-1"></div>
            <TabButton active={activeTab === 'submit'} onClick={() => setActiveTab('submit')} label="Submit New" icon="fas fa-plus" highlight />
          </div>

          {activeTab !== 'submit' ? (
            <div className="space-y-4">
              <AnnouncementCard 
                title="Goa Trip Bonanza Qualification Extended!"
                type="offers" date="Oct 14, 2023" status="approved"
                content="Great news! The qualification period for the Goa Trip Bonanza has been extended by 15 days. All pending direct matches will count."
              />
              <AnnouncementCard 
                title="Q3 Annual Meetup - Hyderabad"
                type="events" date="Oct 10, 2023" status="approved"
                content="Join us for the Q3 regional meetup in Hyderabad. Keynote speakers and awards ceremony for top performers."
              />
            </div>
          ) : (
            <SubmitAnnouncementForm />
          )}
        </div>
      )}
    </div>
  );
}

function TabButton({ active, onClick, label, icon, highlight }: { active: boolean, onClick: () => void, label: string, icon?: string, highlight?: boolean }) {
  return (
    <button
      onClick={onClick}
      className={`px-6 py-4 font-medium text-sm transition-all relative flex items-center gap-2 ${
        active ? (highlight ? "text-sky-600 bg-sky-50" : "text-gray-900 bg-gray-50") : (highlight ? "text-sky-600 hover:bg-sky-50" : "text-gray-500 hover:text-gray-900 hover:bg-gray-50")
      }`}
    >
      {icon && <i className={icon}></i>} {label}
      {active && (
        <div className={`absolute bottom-0 left-0 right-0 h-0.5 ${highlight ? 'bg-sky-500' : 'bg-gray-900'}`}></div>
      )}
    </button>
  );
}

function AnnouncementCard({ title, type, date, status, content }: any) {
  const isOffer = type === 'offers';
  const typeColor = isOffer ? "bg-emerald-50 text-emerald-700 border-emerald-200" : "bg-sky-50 text-sky-700 border-sky-200";
  
  return (
    <div className={`p-5 rounded-xl bg-white border border-gray-200 shadow-sm border-l-4 ${isOffer ? 'border-l-emerald-500' : 'border-l-sky-500'} hover:shadow-md transition-shadow group`}>
      <div className="flex justify-between items-start mb-2">
        <div>
          <h3 className="font-bold text-gray-900 text-lg group-hover:text-sky-600 transition-colors">{title}</h3>
          <div className="flex items-center gap-3 mt-2">
            <span className={`px-2 py-0.5 rounded text-xs font-medium border ${typeColor} uppercase tracking-wider`}>
              {type}
            </span>
            <span className="text-xs text-gray-500 flex items-center gap-1"><i className="far fa-calendar-alt"></i> {date}</span>
          </div>
        </div>
        <span className="px-2 py-1 bg-emerald-100 text-emerald-800 text-xs rounded-lg font-bold">
          {status}
        </span>
      </div>
      <p className="text-gray-600 text-sm mt-3 leading-relaxed">{content}</p>
    </div>
  );
}

function SubmitAnnouncementForm() {
  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
      <div className="p-6 border-b border-gray-200 bg-sky-50 flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-sky-100 flex items-center justify-center text-sky-600">
          <i className="fas fa-paper-plane"></i>
        </div>
        <div>
          <h3 className="font-bold text-sky-900">Broadcast New Announcement</h3>
          <p className="text-xs text-sky-700">Submit an announcement on behalf of the selected member.</p>
        </div>
      </div>
      <div className="p-8 max-w-3xl">
        <form className="space-y-6">
          <div className="grid grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-bold text-gray-900 mb-2">Category <span className="text-rose-500">*</span></label>
              <select className="w-full bg-gray-50 border border-gray-200 rounded-lg py-2.5 px-3 text-gray-900 focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition-all">
                <option>Offer & Bonanza</option>
                <option>Corporate Event</option>
                <option>General News</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-bold text-gray-900 mb-2">Visible To <span className="text-rose-500">*</span></label>
              <div className="flex gap-4 mt-2">
                <label className="flex items-center gap-2 cursor-pointer text-sm font-medium text-gray-700">
                  <input type="radio" name="vis" className="text-sky-600 focus:ring-sky-600" /> MNR
                </label>
                <label className="flex items-center gap-2 cursor-pointer text-sm font-medium text-gray-700">
                  <input type="radio" name="vis" className="text-sky-600 focus:ring-sky-600" /> VGK
                </label>
                <label className="flex items-center gap-2 cursor-pointer text-sm font-medium text-gray-700">
                  <input type="radio" name="vis" defaultChecked className="text-sky-600 focus:ring-sky-600" /> Both
                </label>
              </div>
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-bold text-gray-900 mb-2">Title <span className="text-rose-500">*</span></label>
            <input type="text" className="w-full bg-gray-50 border border-gray-200 rounded-lg py-2.5 px-3 text-gray-900 focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition-all" placeholder="Enter headline..." />
          </div>
          
          <div>
            <label className="block text-sm font-bold text-gray-900 mb-2">Description <span className="text-rose-500">*</span></label>
            <textarea rows={5} className="w-full bg-gray-50 border border-gray-200 rounded-lg py-3 px-4 text-gray-900 focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition-all" placeholder="Enter detailed announcement content..."></textarea>
          </div>
          
          <div className="p-4 border border-dashed border-gray-300 rounded-xl bg-gray-50 text-center">
            <i className="fas fa-cloud-upload-alt text-3xl text-gray-400 mb-2"></i>
            <h4 className="font-medium text-gray-900 mb-1">Upload Media Files</h4>
            <p className="text-xs text-gray-500 mb-4">Min 3 files required. Photos up to 10, Videos max 3 min.</p>
            <button type="button" className="px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-100 transition-colors shadow-sm">
              Browse Files
            </button>
          </div>

          <div className="pt-4 flex gap-3">
            <button type="button" className="px-6 py-3 bg-gray-900 hover:bg-black text-white font-bold rounded-lg shadow-sm transition-colors flex items-center gap-2">
              <i className="fas fa-paper-plane"></i> Broadcast Now
            </button>
            <button type="button" className="px-6 py-3 bg-white border border-gray-200 text-gray-700 font-bold rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
              Save Draft
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
