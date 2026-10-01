import os
import re

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

js_path = os.path.join(base_dir, "frontend", "public", "js", "menu-master.js")
ts_path = os.path.join(base_dir, "mobile", "src", "constants", "menu-master.ts")

with open(js_path, "r", encoding="utf-8", errors="ignore") as f:
    js_text = f.read()

# Find start of MENU_MASTER array
start_idx = js_text.find("var MENU_MASTER = _win.MENU_MASTER = _win.MENU_MASTER || [")
if start_idx == -1:
    start_idx = js_text.find("var MENU_MASTER = [")

start_bracket = js_text.find("[", start_idx)

# Find end of MENU_MASTER array by counting brackets
bracket_count = 0
end_bracket = -1
for i in range(start_bracket, len(js_text)):
    if js_text[i] == '[':
        bracket_count += 1
    elif js_text[i] == ']':
        bracket_count -= 1
        if bracket_count == 0:
            end_bracket = i
            break

array_str = js_text[start_bracket:end_bracket + 1]

ts_content = f"""export interface SidebarItem {{
  menu_code: string;
  label: string;
  route: string;
  audience?: string[];
  icon?: string;
}}

export interface SidebarSubSection {{
  sub_section_code: string;
  sub_section_label: string;
  items: SidebarItem[];
}}

export interface SidebarSection {{
  section_code: string;
  section_label: string;
  order: number;
  items?: SidebarItem[];
  subSections?: SidebarSubSection[];
}}

export const MENU_MASTER: SidebarSection[] = {array_str};

export function getAllMenuItems(): (SidebarItem & {{ section_code: string; section_label: string; section_order: number; sub_section_code?: string; sub_section_label?: string }})[] {{
  const items: any[] = [];
  MENU_MASTER.forEach(section => {{
    if (section.items) {{
      section.items.forEach(item => {{
        items.push({{
          ...item,
          section_code: section.section_code,
          section_label: section.section_label,
          section_order: section.order
        }});
      }});
    }}
    if (section.subSections) {{
      section.subSections.forEach(subSection => {{
        subSection.items.forEach(item => {{
          items.push({{
            ...item,
            section_code: section.section_code,
            section_label: section.section_label,
            section_order: section.order,
            sub_section_code: subSection.sub_section_code,
            sub_section_label: subSection.sub_section_label
          }});
        }});
      }});
    }}
  }});
  return items;
}}

export function findMenuByRoute(route: string) {{
  const allItems = getAllMenuItems();
  return allItems.find(item => item.route === route) || null;
}}

export function findMenuByCode(menuCode: string) {{
  const allItems = getAllMenuItems();
  return allItems.find(item => item.menu_code === menuCode) || null;
}}

export function getAllRoutes(): string[] {{
  return getAllMenuItems().map(item => item.route);
}}

export function getSectionByOrder(order: number): SidebarSection | null {{
  return MENU_MASTER.find(section => section.order === order) || null;
}}

export function getTotalMenuCount(): number {{
  return getAllMenuItems().length;
}}
"""

with open(ts_path, "w", encoding="utf-8") as f:
    f.write(ts_content)

print(f"Successfully synchronized {ts_path} from {js_path}! New size: {os.path.getsize(ts_path)} bytes")

