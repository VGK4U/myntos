"use client";

import { useState } from "react";

// Mock Data
const MOCK_CONVERSATIONS = [
  { id: 1, name: "Ramesh Sharma", phone: "+91 98765 43210", lastMessage: "Yes, I am interested in the 3BHK flat.", time: "10:45 AM", unread: 2, online: true, avatar: "R" },
  { id: 2, name: "Sunita Verma", phone: "+91 99887 76655", lastMessage: "Can you send the location pin?", time: "Yesterday", unread: 0, online: false, avatar: "S" },
  { id: 3, name: "Anil Kumar", phone: "+91 91234 56789", lastMessage: "Thanks for the brochure.", time: "Monday", unread: 0, online: true, avatar: "A" },
  { id: 4, name: "Meera Reddy", phone: "+91 98888 77777", lastMessage: "I will call you tomorrow morning.", time: "Aug 10", unread: 0, online: false, avatar: "M" },
];

const MOCK_MESSAGES = [
  { id: 1, sender: "bot", text: "Hi Ramesh, thank you for your interest in MyntReal properties. Are you looking for flats or plots?", time: "10:30 AM" },
  { id: 2, sender: "user", text: "Yes, I am interested in the 3BHK flat.", time: "10:45 AM" },
];

export default function WhatsAppInboxPage() {
  const [activeChat, setActiveChat] = useState(MOCK_CONVERSATIONS[0]);
  const [messageText, setMessageText] = useState("");
  const [messages, setMessages] = useState(MOCK_MESSAGES);

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!messageText.trim()) return;

    // Add message to mock list
    setMessages([...messages, { 
      id: Date.now(), 
      sender: "agent", 
      text: messageText, 
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) 
    }]);
    setMessageText("");
  };

  return (
    <div className="h-[calc(100vh-140px)] animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-7xl mx-auto flex flex-col">
      <div className="flex justify-between items-end mb-4">
        <div>
          <h1 className="text-2xl font-extrabold text-gray-900 tracking-tight mb-1">WA Inbox (CRM)</h1>
          <p className="text-gray-500">Manage all your WhatsApp Meta interactions directly from the CRM.</p>
        </div>
        <div className="flex gap-2">
          <button className="px-4 py-2 bg-emerald-600 text-white font-bold rounded-lg shadow-sm hover:bg-emerald-700 transition-colors text-sm">
            <i className="fas fa-broadcast-tower mr-2"></i> Broadcast Message
          </button>
        </div>
      </div>

      <div className="flex-1 bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden flex">
        {/* Left Sidebar - Conversations */}
        <div className="w-1/3 border-r border-gray-200 flex flex-col bg-gray-50/30">
          <div className="p-4 border-b border-gray-200 bg-gray-50">
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <i className="fas fa-search text-gray-400"></i>
              </div>
              <input
                type="text"
                placeholder="Search chats..."
                className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:ring-emerald-500 focus:border-emerald-500"
              />
            </div>
          </div>
          
          <div className="flex-1 overflow-y-auto">
            <ul className="divide-y divide-gray-100">
              {MOCK_CONVERSATIONS.map((chat) => (
                <li 
                  key={chat.id}
                  onClick={() => setActiveChat(chat)}
                  className={`p-4 cursor-pointer hover:bg-gray-50 transition-colors ${activeChat.id === chat.id ? 'bg-emerald-50 hover:bg-emerald-50 relative' : ''}`}
                >
                  {activeChat.id === chat.id && (
                    <div className="absolute left-0 top-0 bottom-0 w-1 bg-emerald-500"></div>
                  )}
                  <div className="flex items-center gap-3">
                    <div className="relative">
                      <div className="w-12 h-12 rounded-full bg-gray-200 flex items-center justify-center text-gray-600 font-bold text-lg">
                        {chat.avatar}
                      </div>
                      {chat.online && (
                        <div className="absolute bottom-0 right-0 w-3.5 h-3.5 bg-emerald-500 border-2 border-white rounded-full"></div>
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex justify-between items-baseline mb-1">
                        <h4 className={`text-sm truncate ${activeChat.id === chat.id ? 'font-bold text-gray-900' : 'font-medium text-gray-900'}`}>
                          {chat.name}
                        </h4>
                        <span className={`text-xs ${chat.unread > 0 ? 'text-emerald-600 font-bold' : 'text-gray-400'}`}>
                          {chat.time}
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <p className={`text-xs truncate ${chat.unread > 0 ? 'text-gray-900 font-medium' : 'text-gray-500'}`}>
                          {chat.lastMessage}
                        </p>
                        {chat.unread > 0 && (
                          <div className="w-5 h-5 rounded-full bg-emerald-500 flex items-center justify-center text-white text-[10px] font-bold">
                            {chat.unread}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Right Main Area - Chat Window */}
        <div className="w-2/3 flex flex-col bg-[#efeae2]">
          {/* Chat Header */}
          <div className="h-16 px-6 border-b border-gray-200 bg-white flex items-center justify-between shrink-0 shadow-sm z-10">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center text-gray-600 font-bold">
                {activeChat.avatar}
              </div>
              <div>
                <h3 className="font-bold text-gray-900 leading-tight">{activeChat.name}</h3>
                <p className="text-xs text-gray-500 leading-tight">{activeChat.phone}</p>
              </div>
            </div>
            <div className="flex gap-4 text-gray-400">
              <button className="hover:text-gray-600 transition-colors"><i className="fas fa-video"></i></button>
              <button className="hover:text-gray-600 transition-colors"><i className="fas fa-phone-alt"></i></button>
              <button className="hover:text-gray-600 transition-colors"><i className="fas fa-ellipsis-v"></i></button>
            </div>
          </div>

          {/* Chat Messages */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-[url('https://i.pinimg.com/736x/8c/98/99/8c98994518b575bfd8c949e91d20548b.jpg')] bg-cover bg-center">
            <div className="text-center mb-6">
              <span className="bg-white/80 backdrop-blur px-3 py-1 rounded-lg text-xs font-medium text-gray-600 shadow-sm inline-block">
                Today
              </span>
            </div>

            {messages.map((msg) => (
              <div key={msg.id} className={`flex ${msg.sender === 'user' ? 'justify-start' : 'justify-end'}`}>
                <div className={`max-w-[70%] rounded-lg px-4 py-2 shadow-sm relative ${
                  msg.sender === 'user' 
                    ? 'bg-white rounded-tl-none' 
                    : 'bg-[#d9fdd3] rounded-tr-none'
                }`}>
                  {msg.sender === 'bot' && (
                    <div className="text-[10px] font-bold text-emerald-600 mb-1 flex items-center gap-1">
                      <i className="fas fa-robot"></i> Automated Greeting
                    </div>
                  )}
                  {msg.sender === 'agent' && (
                    <div className="text-[10px] font-bold text-gray-500 mb-1 flex items-center gap-1">
                      <i className="fas fa-headset"></i> You
                    </div>
                  )}
                  <p className="text-sm text-gray-800">{msg.text}</p>
                  <div className="text-[10px] text-gray-400 text-right mt-1 flex justify-end items-center gap-1">
                    {msg.time}
                    {(msg.sender === 'bot' || msg.sender === 'agent') && (
                      <i className="fas fa-check-double text-blue-500"></i>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Chat Input */}
          <div className="p-4 bg-gray-50 border-t border-gray-200 shrink-0">
            <form onSubmit={handleSendMessage} className="flex gap-2">
              <button type="button" className="p-3 text-gray-500 hover:text-gray-700 transition-colors rounded-full hover:bg-gray-200 shrink-0">
                <i className="fas fa-paperclip text-xl"></i>
              </button>
              <input
                type="text"
                value={messageText}
                onChange={(e) => setMessageText(e.target.value)}
                placeholder="Type a message"
                className="flex-1 px-4 py-3 border-none rounded-xl text-sm bg-white focus:ring-0 shadow-sm"
              />
              {messageText.trim() ? (
                <button type="submit" className="p-3 text-white bg-emerald-600 hover:bg-emerald-700 transition-colors rounded-full shrink-0 shadow-sm flex items-center justify-center w-[48px] h-[48px]">
                  <i className="fas fa-paper-plane"></i>
                </button>
              ) : (
                <button type="button" className="p-3 text-gray-500 hover:text-gray-700 transition-colors rounded-full hover:bg-gray-200 shrink-0 flex items-center justify-center w-[48px] h-[48px]">
                  <i className="fas fa-microphone text-xl"></i>
                </button>
              )}
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
