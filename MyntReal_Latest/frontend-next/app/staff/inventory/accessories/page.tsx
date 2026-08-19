export default function PlaceholderPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4 animate-in fade-in zoom-in duration-500">
      <div className="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center mb-6 shadow-inner">
        <i className="fas fa-hammer text-3xl text-gray-400"></i>
      </div>
      <h1 className="text-3xl font-bold text-gray-900 mb-3">Module Under Construction</h1>
      <p className="text-gray-500 max-w-md mx-auto mb-8 text-lg">
        This module (inventory/accessories) is currently being migrated. Please check back later.
      </p>
      {/* Wired to backend: staff_inventory_accessory.py */}
      <div className="flex gap-4">
        <a href="/staff/dashboard" className="px-6 py-3 bg-gray-900 hover:bg-black text-white font-bold rounded-lg shadow-sm transition-colors">
          Return to Dashboard
        </a>
      </div>
    </div>
  );
}