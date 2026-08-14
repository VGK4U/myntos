import os
import re

NAV_FILE = r"C:\Desktop\VGK4U\MyntReal_Latest\frontend-next\lib\navigation.ts"
APP_DIR = r"C:\Desktop\VGK4U\MyntReal_Latest\frontend-next\app"

TEMPLATE = """export default function PlaceholderPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4 animate-in fade-in zoom-in duration-500">
      <div className="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center mb-6 shadow-inner">
        <i className="fas fa-hammer text-3xl text-gray-400"></i>
      </div>
      <h1 className="text-3xl font-bold text-gray-900 mb-3">Module Under Construction</h1>
      <p className="text-gray-500 max-w-md mx-auto mb-8 text-lg">
        This module is currently being migrated to the new Premium Light Theme architecture. Please check back later.
      </p>
      <div className="flex gap-4">
        <a href="/staff/dashboard" className="px-6 py-3 bg-gray-900 hover:bg-black text-white font-bold rounded-lg shadow-sm transition-colors">
          Return to Dashboard
        </a>
      </div>
    </div>
  );
}
"""

def main():
    if not os.path.exists(NAV_FILE):
        print(f"Error: Nav file not found at {NAV_FILE}")
        return

    with open(NAV_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # Find all routes, e.g., route: "/staff/tasks/day-planner"
    routes = re.findall(r'route:\s*["\']([^"\']+)["\']', content)
    
    created_count = 0
    for route in routes:
        # Ignore external links or anchors
        if route.startswith("http") or "#" in route:
            # Handle routes like /staff/kra-status#reviews by taking the base part
            route = route.split("#")[0]
            
        # Remove leading slash
        clean_route = route.lstrip("/")
        
        target_dir = os.path.join(APP_DIR, clean_route.replace("/", os.sep))
        target_file = os.path.join(target_dir, "page.tsx")
        
        if not os.path.exists(target_file):
            os.makedirs(target_dir, exist_ok=True)
            with open(target_file, "w", encoding="utf-8") as out_f:
                out_f.write(TEMPLATE)
            print(f"Created placeholder: {route}")
            created_count += 1
            
    print(f"\nDone! Created {created_count} placeholder pages.")

if __name__ == "__main__":
    main()
