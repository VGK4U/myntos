"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";

interface ChatContact {
  id: string; // from_phone
  phone: string;
  name: string;
  last_message: string;
  last_message_time: string;
  unread_count: number;
  is_online: boolean;
}

export default function WhatsAppInboxPage() {
  const { token } = useStaffAuth();
  const [contacts, setContacts] = useState<ChatContact[]>([]);
  const [activeChat, setActiveChat] = useState<ChatContact | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [messageInput, setMessageInput] = useState("");

  useEffect(() => {
    if (!token) return;
    
    const fetchInbox = async () => {
      try {
        setLoading(true);
        const res = await fetch(`${getApiUrl()}/api/v1/whatsapp/inbox`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        });
        
        if (res.ok) {
          const json = await res.json();
          if (json.success && json.data) {
            const mapped = json.data.map((item: any) => ({
              id: item.from_phone,
              phone: item.from_phone,
              name: item.resolved_name || item.from_name || item.from_phone,
              last_message: item.last_message || "Attachment / Media",
              last_message_time: item.last_activity ? new Date(item.last_activity).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : "",
              unread_count: item.unread_count || 0,
              is_online: false
            }));
            setContacts(mapped);
            if (mapped.length > 0) {
              setActiveChat(mapped[0]);
            }
          }
        }
      } catch (error) {
        console.error("Failed to fetch inbox", error);
      } finally {
        setLoading(false);
      }
    };
    
    fetchInbox();
  }, [token]);

  const filteredContacts = contacts.filter(c => 
    c.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
    c.phone.includes(searchTerm)
  );

  return (
    <div className="p-6 max-w-7xl mx-auto h-[calc(100vh-80px)] flex flex-col">
      <div className="flex justify-between items-end mb-6 shrink-0">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">WhatsApp Inbox</h1>
          <p className="text-sm text-gray-500 mt-2">Manage customer conversations directly from your CRM.</p>
        </div>
        <div className="flex space-x-3">
          <button className="px-4 py-2 bg-green-500 text-white font-medium rounded-lg shadow-sm hover:bg-green-600 transition-colors">
            <i className="fas fa-paper-plane mr-2"></i> Bulk Broadcast
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 flex flex-1 overflow-hidden min-h-0">
        {/* Sidebar Contacts */}
        <div className="w-1/3 border-r border-gray-100 flex flex-col bg-gray-50/50">
          <div className="p-4 border-b border-gray-100 bg-white">
            <div className="relative">
              <i className="fas fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"></i>
              <input 
                type="text" 
                placeholder="Search chats..." 
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-2 w-full border border-gray-200 rounded-lg text-sm focus:ring-2 focus:border-green-500 outline-none bg-gray-50" 
              />
            </div>
          </div>
          <div className="flex-1 overflow-y-auto">
            {filteredContacts.map(contact => (
              <div 
                key={contact.id} 
                onClick={() => setActiveChat(contact)}
                className={`p-4 border-b border-gray-50 flex items-center cursor-pointer transition-colors ${
                  activeChat?.id === contact.id ? 'bg-green-50' : 'hover:bg-gray-100/50'
                }`}
              >
                <div className="relative shrink-0">
                  <div className="w-12 h-12 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center font-bold">
                    {contact.name.charAt(0)}
                  </div>
                  {contact.is_online && (
                    <div className="absolute bottom-0 right-0 w-3 h-3 bg-green-500 border-2 border-white rounded-full"></div>
                  )}
                </div>
                <div className="ml-3 flex-1 min-w-0">
                  <div className="flex justify-between items-center mb-1">
                    <h3 className="text-sm font-bold text-gray-900 truncate">{contact.name}</h3>
                    <span className="text-[10px] font-medium text-gray-500 shrink-0">{contact.last_message_time}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <p className="text-xs text-gray-500 truncate pr-2">{contact.last_message}</p>
                    {contact.unread_count > 0 && (
                      <span className="w-5 h-5 rounded-full bg-green-500 text-white flex items-center justify-center text-[10px] font-bold shrink-0">
                        {contact.unread_count}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Chat Area */}
        {activeChat ? (
          <div className="w-2/3 flex flex-col bg-[#efeae2]">
            {/* Chat Header */}
            <div className="p-4 bg-white border-b border-gray-200 flex justify-between items-center shrink-0 shadow-sm z-10">
              <div className="flex items-center">
                <div className="w-10 h-10 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center font-bold mr-3">
                  {activeChat.name.charAt(0)}
                </div>
                <div>
                  <h3 className="font-bold text-gray-900 leading-tight">{activeChat.name}</h3>
                  <p className="text-xs text-gray-500">{activeChat.phone} • {activeChat.is_online ? 'Online' : 'Offline'}</p>
                </div>
              </div>
              <div className="flex space-x-3 text-gray-500">
                <button className="hover:text-indigo-600 transition-colors p-2"><i className="fas fa-phone"></i></button>
                <button className="hover:text-indigo-600 transition-colors p-2"><i className="fas fa-video"></i></button>
                <button className="hover:text-indigo-600 transition-colors p-2"><i className="fas fa-ellipsis-v"></i></button>
              </div>
            </div>
            
            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              <div className="flex justify-center mb-6">
                <span className="bg-white/80 px-3 py-1 rounded-lg text-xs font-medium text-gray-500 shadow-sm">Today</span>
              </div>
              <div className="flex justify-end">
                <div className="bg-[#dcf8c6] rounded-lg rounded-tr-none p-3 max-w-[70%] shadow-sm relative pb-5">
                  <p className="text-sm text-gray-800">Hi {activeChat.name}, this is regarding your inquiry about our new services.</p>
                  <span className="text-[10px] text-gray-500 absolute bottom-1 right-2">
                    10:15 AM <i className="fas fa-check-double text-blue-500 ml-1"></i>
                  </span>
                </div>
              </div>
              <div className="flex justify-start">
                <div className="bg-white rounded-lg rounded-tl-none p-3 max-w-[70%] shadow-sm relative pb-5">
                  <p className="text-sm text-gray-800">{activeChat.last_message}</p>
                  <span className="text-[10px] text-gray-400 absolute bottom-1 right-2">
                    {activeChat.last_message_time}
                  </span>
                </div>
              </div>
            </div>

            {/* Input Area */}
            <div className="p-3 bg-gray-100 border-t border-gray-200 shrink-0 flex items-center space-x-2">
              <button className="text-gray-500 hover:text-gray-700 p-2 text-xl"><i className="far fa-smile"></i></button>
              <button className="text-gray-500 hover:text-gray-700 p-2 text-xl"><i className="fas fa-paperclip"></i></button>
              <input 
                type="text" 
                placeholder="Type a message..." 
                value={messageInput}
                onChange={(e) => setMessageInput(e.target.value)}
                className="flex-1 bg-white border-none rounded-full px-4 py-3 text-sm focus:ring-0 outline-none shadow-sm"
              />
              {messageInput ? (
                <button className="bg-green-500 text-white w-10 h-10 rounded-full flex items-center justify-center hover:bg-green-600 transition-colors shadow-sm">
                  <i className="fas fa-paper-plane"></i>
                </button>
              ) : (
                <button className="text-gray-500 hover:text-gray-700 p-2 text-xl">
                  <i className="fas fa-microphone"></i>
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="w-2/3 flex flex-col items-center justify-center bg-gray-50 text-gray-400">
            <i className="fab fa-whatsapp text-6xl mb-4 opacity-20"></i>
            <p className="font-medium">Select a chat to start messaging</p>
          </div>
        )}
      </div>
    </div>
  );
}
