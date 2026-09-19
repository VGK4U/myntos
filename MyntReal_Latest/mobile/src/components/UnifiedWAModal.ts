/**
 * Unified WhatsApp Dispatch Modal for Mobile
 * DC Protocol: DC_MOBILE_WA_MODAL_001
 * 
 * Features:
 * - Direct dispatch via Scanned Connected Bot (Port 5002 /api/v1/whatsapp/send-message)
 * - Automatic sender identification & signature appending for complete staff tracking
 * - Direct WhatsApp (wa.me) fallback
 * - Quick contextual templates
 * - Live dispatch feedback
 */

import { apiService } from '../services/api.service';
import { authService } from '../services/auth.service';

export interface WAModalOptions {
  phone: string;
  name?: string;
  leadId?: number | string;
  context?: string;
  defaultMessage?: string;
  segment?: string;
}

const QUICK_TEMPLATES: Record<string, { label: string; text: string }> = {
  greeting: {
    label: '👋 Welcome & Introduction',
    text: 'Namaskaram! Thank you for connecting with MyntReal. I am your dedicated relationship manager. Please let me know how I may assist you with your project today.'
  },
  bank_update: {
    label: '🏦 Bank Loan Update',
    text: 'Dear Customer, your bank file is currently under active processing. Our team is following up with the branch for swift approval and sanction.'
  },
  net_meter: {
    label: '⚡ Net Meter & EB',
    text: 'Dear Customer, your DISCOM Net Metering and EB service documentation is progressing as scheduled. We will update you once the inspection is cleared.'
  },
  payment: {
    label: '💰 Payment / Balance Follow-up',
    text: 'Dear Customer, this is a gentle reminder regarding the pending balance for your project. Kindly arrange the clearance at your earliest convenience.'
  },
  site_visit: {
    label: '📍 Location & Site Visit',
    text: 'Dear Customer, our technical field staff is scheduled to visit your site. Kindly let us know if you need to coordinate the visit time.'
  }
};

interface DigitalCatalogInfo {
  name: string;
  btnLabel: string;
  segmentSlug: string;
  catalogSlug: string;
  desc: string;
  messages: {
    te: (cName: string, url: string) => string;
    en: (cName: string, url: string) => string;
    hi: (cName: string, url: string) => string;
    ta: (cName: string, url: string) => string;
  };
}

const DIGITAL_CATALOGS: Record<string, DigitalCatalogInfo> = {
  solar: {
    name: 'Solar Rooftop & EPC',
    btnLabel: 'Solar',
    segmentSlug: 'solar',
    catalogSlug: 'commercial-residential-solar',
    desc: 'Sends personalized Har Ghar Solar Digital Catalog link with 90% savings, ₹78,000 subsidy & ₹1 scheme details.',
    messages: {
      te: (cName, url) => `నమస్కారం ${cName} గారు! 🙏\n\nMyntReal Har Ghar Solar డిజిటల్ క్యాటలాగ్ & సబ్సిడీ కాలిక్యులేటర్ లింక్ ఇక్కడ చూడవచ్చు:\n👉 ${url}\n\n⚡ ముఖ్య వివరాలు:\n• కరెంట్ బిల్లు 90% వరకు ఆదా\n• ₹78,000 కేంద్ర ప్రభుత్వ సబ్సిడీ (PM Surya Ghar)\n• ₹1 కే సోలార్ & సులభ బ్యాంక్ లోన్ EMI ఆప్షన్స్\n• Tier-1 బ్రాండ్లు & 25 సంవత్సరాల వారంటీ\n\nపై లింక్ ఓపెన్ చేసి మీ ఇంటి కరెంట్ బిల్లుకు సరిపోయే ప్లాన్ మరియు సేవింగ్స్ కాలిక్యులేట్ చేసుకోగలరు.`,
      en: (cName, url) => `Namaskaram ${cName}! 🙏\n\nHere is your official MyntReal Har Ghar Solar Digital Catalog & Subsidy Estimator link:\n👉 ${url}\n\n⚡ Highlights:\n• Reduce your power bill by up to 90%\n• Up to ₹78,000 Central Govt Subsidy (PM Surya Ghar)\n• "Solar for ₹1" zero-collateral bank EMI plans\n• Authorized Tier-1 Brands & 25-Year Performance Warranty\n\nClick the link above to calculate your recommended capacity, savings & instant quotation.`,
      hi: (cName, url) => `नमस्ते ${cName} जी! 🙏\n\nMyntReal हर घर सोलर डिजिटल कैटलॉग और सब्सिडी कैलकुलेटर लिंक यहाँ देखें:\n👉 ${url}\n\n⚡ मुख्य लाभ:\n• बिजली बिल में 90% तक बचत\n• ₹78,000 तक केंद्र सरकारी सब्सिडी (PM सूर्य घर योजना)\n• ₹1 में सोलर और आसान बैंक लोन ईएमआई\n• टियर-1 सोलर ब्रांड्स और 25 साल की वारंटी\n\nकृपया ऊपर दिए गए लिंक पर क्लिक करें और अपनी मासिक बचत की गणना करें।`,
      ta: (cName, url) => `வணக்கம் ${cName}! 🙏\n\nMyntReal ஹர் கர் சோலார் டிஜிட்டல் கேட்லாக் மற்றும் மானிய கால்குலேட்டர் லிங்க்:\n👉 ${url}\n\n⚡ முக்கிய சிறப்பம்சங்கள்:\n• 90% வரை மின் கட்டண சேமிப்பு\n• ₹78,000 மத்திய அரசு மானியம் (PM சூர்யா கர்)\n• ₹1 சோலார் & எளிய வங்கி லோன் EMI தவணைகள்\n• Tier-1 சோலார் பிராண்டுகள் & 25 வருட வாரண்டி\n\nமேலே உள்ள இணைப்பைக் கிளிக் செய்து உங்கள் மின்சார சேமிப்பைக் கணக்கிடுங்கள்.`
    }
  },
  real_estate: {
    name: 'Premium Real Estate & Townships',
    btnLabel: 'Real Estate',
    segmentSlug: 'real-dreams',
    catalogSlug: 'real-dreams-premium-properties',
    desc: 'Sends Real Dreams catalog with RERA-approved luxury villas, gated open plots & prime commercial spaces.',
    messages: {
      te: (cName, url) => `నమస్కారం ${cName} గారు! 🙏\n\n🏡 *VGK Real Dreams — RERA & DTCP ఆమోదిత ప్రీమియం గేటెడ్ టౌన్‌షిప్స్*\n\nమీ కోసం అధికారిక రియల్ డ్రీమ్స్ డిజిటల్ క్యాటలాగ్ లింక్:\n👉 ${url}\n\n🌟 *ప్రాజెక్ట్ విశేషాలు & చట్టబద్ధత:*\n• 100% RERA & DTCP/VMRDA ఆమోదిత లేఅవుట్స్ & లగ్జరీ విల్లాస్\n• తక్షణ స్పాట్ రిజిస్ట్రేషన్ గ్యారెంటీ & 30 సం. క్లియర్ టైటిల్\n• SBI, HDFC, ICICI బ్యాంకుల ద్వారా 80% వరకు లోన్ సదుపాయం\n• 40+ ఆధునిక వసతులు: 40ft BT రోడ్లు, భూగర్భ విద్యుత్, సోలార్ లైట్లు, క్లబ్‌హౌస్\n• ప్లాట్ సైజులు: 167, 200, 267 & 500 చ.గ. (చ.గ. ₹18,500 నుండి)\n\n🔍 *ధృవీకరించబడిన స్టాఫ్ కాన్ఫిగరేషన్ పోర్టల్:*\n👉 http://localhost:5001/staff/configuration/catalog\n\n🛒 *రియల్ డ్రీమ్స్ ఈ-కామ్ మార్కెట్‌ప్లేస్‌లో ప్లాట్స్ చూడండి:*\n👉 http://localhost:5001/ecom?segment=real-dreams\n\nఉచిత VIP సైట్ విజిట్ కోసం సంప్రదించండి.`,
      en: (cName, url) => `Namaskaram ${cName}! 🙏\n\n🏡 *VGK Real Dreams — Verified Gated Communities & Solar Townships*\n\nHere is your official Real Dreams Premium Properties Digital Catalog:\n👉 ${url}\n\n🌟 *Project Highlights & Legal Genuineness:*\n• 100% RERA & DTCP/VMRDA Approved Gated Villa Layouts\n• Immediate Spot Registration Guarantee with 30-year clear legal title\n• Bank Loan Approvals up to 80% from SBI, HDFC, and ICICI Bank\n• 40+ Lifestyle Amenities: 40ft/33ft BT roads, underground power, solar lighting\n• Plot Sizes: 167, 200, 267 & 500 Sq. Yards (from ₹18,500/yd)\n\n🔍 *Central Verified Property Configuration Portal:*\n👉 http://localhost:5001/staff/configuration/catalog\n\n🛒 *Browse Live Verified Listings on Real Dreams E-Com:*\n👉 http://localhost:5001/ecom?segment=real-dreams\n\nComplimentary chauffeur AC cab pickup available for site visits!`,
      hi: (cName, url) => `नमस्ते ${cName} जी! 🙏\n\nVGK Real Dreams प्रीमियम प्रॉपर्टीज डिजिटल कैटलॉग लिंक:\n👉 ${url}\n\n🏡 100% RERA & टाउनशिप अनुमोदित प्लॉट्स एवं विला\n• 80% तक बैंक लोन स्वीकृत (SBI, HDFC, ICICI)\n• तत्काल रजिस्ट्री एवं स्पष्ट मालिकाना हक\n\nई-कॉमर्स पर प्लॉट्स देखें: http://localhost:5001/ecom?segment=real-dreams\nकैटलॉग वेरिफिकेशन: http://localhost:5001/staff/configuration/catalog`,
      ta: (cName, url) => `வணக்கம் ${cName}! 🙏\n\nVGK Real Dreams பிரீமியம் ரியல் எஸ்டேட் டிஜிட்டல் கேட்லாக் லிங்க்:\n👉 ${url}\n\n100% RERA அங்கீகரிக்கப்பட்ட சொத்துக்கள் & 80% வங்கி கடன் வசதி!\nஇ-காமர்ஸ் மூலம் பார்வையிட: http://localhost:5001/ecom?segment=real-dreams`
    }
  },
  ev_b2c: {
    name: 'Smart Electric 2-Wheelers (B2C)',
    btnLabel: 'EV 2W',
    segmentSlug: 'ev-b2c',
    catalogSlug: 'ev-smart-commuter',
    desc: 'Sends Smart Electric 2W catalog with 120km range, LFP battery, mobile app & ₹0.25/km running cost.',
    messages: {
      te: (cName, url) => `నమస్కారం ${cName} గారు! 🙏\n\nMyntReal Smart Electric 2-Wheelers డిజిటల్ క్యాటలాగ్ లింక్ ఇక్కడ చూడవచ్చు:\n👉 ${url}\n\n⚡ ముఖ్య విశేషాలు:\n• ఒక్క ఛార్జ్‌తో 120+ కి.మీ రియల్-వరల్డ్ రేంజ్\n• అధునాతన LFP బ్యాటరీ టెక్నాలజీ & లాంగ్ లైఫ్\n• డిజిటల్ స్మార్ట్ కన్సోల్, GPS ట్రాకింగ్ & రీజెనరేటివ్ బ్రేకింగ్\n• అతి తక్కువ రన్నింగ్ కాస్ట్ — కి.మీ కి కేవలం 25 పైసలు\n\nపై లింక్ క్లిక్ చేసి లేటెస్ట్ ఈవీ మోడల్స్, ఫీచర్లు మరియు టెస్ట్ రైడ్ బుక్ చేసుకోండి.`,
      en: (cName, url) => `Namaskaram ${cName}! 🙏\n\nHere is your official MyntReal Smart Electric 2-Wheelers Digital Catalog link:\n👉 ${url}\n\n⚡ Key Highlights:\n• 120+ km Real-World Range on a single charge\n• Ultra-safe LFP Battery with extended warranty\n• Smart Mobile App Connectivity, GPS & Digital Cockpit\n• Running cost as low as ₹0.25 per kilometer\n\nClick the link above to explore EV models, color variants & book your free test ride.`,
      hi: (cName, url) => `नमस्ते ${cName} जी! 🙏\n\nMyntReal स्मार्ट इलेक्ट्रिक 2-व्हीलर्स डिजिटल कैटलॉग लिंक यहाँ देखें:\n👉 ${url}\n\n⚡ मुख्य विशेषताएं:\n• सिंगल चार्ज में 120+ किमी की रेंज\n• आधुनिक सुरक्षित LFP बैटरी एवं लंबी वारंटी\n• स्मार्ट मोबाइल कनेक्टिविटी और डिजिटल फीचर्स\n• पेट्रोल की तुलना में 85% तक की बचत (25 पैसे/किमी)\n\nकृपया ऊपर दिए गए लिंक पर क्लिक करें और मॉडल्स देखें व फ्री टेस्ट राइड बुक करें।`,
      ta: (cName, url) => `வணக்கம் ${cName}! 🙏\n\nMyntReal ஸ்மார்ட் எலக்ட்ரிக் 2-வீலர் டிஜிட்டல் கேட்லாக் லிங்க்:\n👉 ${url}\n\n⚡ முக்கிய சிறப்பம்சங்கள்:\n• ஒரு சார்ஜில் 120+ கிமீ ரேஞ்ச்\n• அதிநவீன LFP பேட்டரி & நீண்ட கால உத்தரவாதம்\n• பெட்ரோல் செலவில் 85% மிச்சம்\n\nமேலே உள்ள இணைப்பைக் கிளிக் செய்து ஈவி மாடல்களைப் பார்வையிட்டு டெஸ்ட் ரைடு புக் செய்யுங்கள்.`
    }
  },
  ev_b2b: {
    name: 'Commercial EV Fleet & Cargo (B2B)',
    btnLabel: 'EV Commercial Fleet',
    segmentSlug: 'ev-b2b',
    catalogSlug: 'ev-commercial-fleet',
    desc: 'Sends Commercial Fleet catalog with 75% logistics savings, reinforced chassis & 2-min battery swap.',
    messages: {
      te: (cName, url) => `నమస్కారం ${cName} గారు! 🙏\n\nMyntReal Commercial EV Fleet & B2B Cargo డిజిటల్ క్యాటలాగ్ లింక్ ఇక్కడ చూడవచ్చు:\n👉 ${url}\n\n🚚 ముఖ్య ప్రయోజనాలు:\n• లాజిస్టిక్స్ రన్నింగ్ ఖర్చుల్లో 75% భారీ ఆదా\n• భారీ పేలోడ్ సామర్థ్యం కలిగిన హెవీ-డ్యూటీ చాసిస్\n• 2 నిమిషాల క్విక్ బ్యాటరీ స్వాప్పింగ్ & స్మార్ట్ టెలిమాటిక్స్ ఫ్లీట్ ట్రాకింగ్\n• డెలివరీ & బిజినెస్ ఫ్లీట్‌లకు ప్రత్యేక కార్పొరేట్ ఫైనాన్స్\n\nపై లింక్ క్లిక్ చేసి B2B ఫ్లీట్ మోడల్స్ మరియు ROI కాలిక్యులేటర్ చూడండి.`,
      en: (cName, url) => `Namaskaram ${cName}! 🙏\n\nHere is your official MyntReal Commercial EV Fleet & B2B Cargo Digital Catalog link:\n👉 ${url}\n\n🚚 Commercial Fleet Highlights:\n• Slash last-mile logistics operating expenses by 75%\n• Heavy-duty reinforced chassis engineered for Indian cargo loads\n• 2-Minute rapid battery swapping & real-time IoT fleet telematics\n• Attractive commercial leasing & zero-downpayment corporate finance\n\nClick the link above to review vehicle specifications & calculate fleet ROI.`,
      hi: (cName, url) => `नमस्ते ${cName} जी! 🙏\n\nMyntReal कमर्शियल ईवी फ्लीट और B2B कार्गो डिजिटल कैटलॉग लिंक यहाँ देखें:\n👉 ${url}\n\n🚚 प्रमुख लाभ:\n• डिलीवरी और लॉजिस्टिक्स खर्च में 75% तक कटौती\n• भारी माल वहन क्षमता एवं मजबूत चेसिस\n• 2 मिनट की बैटरी स्वैपिंग और लाइव जीपीएस फ्लीट ट्रैकिंग\n• आकर्षक कॉर्पोरेट फाइनेंस और लीजिंग विकल्प\n\nकृपया ऊपर दिए गए लिंक पर क्लिक करके कमर्शियल वाहन विवरण देखें।`,
      ta: (cName, url) => `வணக்கம் ${cName}! 🙏\n\nMyntReal கமர்ஷியல் இ-வாகன கடற்படை (EV Cargo) டிஜிட்டல் கேட்லாக் லிங்க்:\n👉 ${url}\n\n🚚 முக்கிய நன்மைகள்:\n• போக்குவரத்து செலவில் 75% பெரும் சேமிப்பு\n• அதிக எடை சுமக்கும் திறன் மற்றும் நீண்ட ஆயுள்\n• 2 நிமிட பேட்டரி ஸ்வாப் & லைவ் GPS டிராக்கிங்\n\nமேலே உள்ள இணைப்பைக் கிளிக் செய்து விவரங்கள் மற்றும் கார்ப்பரேட் சலுகைகளைக் காண்க.`
    }
  },
  ev_spares: {
    name: 'EV Spares, Chargers & Batteries',
    btnLabel: 'EV Spares',
    segmentSlug: 'ev-spares',
    catalogSlug: 'ev-spares-and-chargers',
    desc: 'Sends EV Spares catalog with OEM components, DC fast chargers, smart BMS & replacement lithium packs.',
    messages: {
      te: (cName, url) => `నమస్కారం ${cName} గారు! 🙏\n\n⚡ *MyntReal & VGK4U — జెన్యూయిన్ EV స్పేర్స్, ఛార్జర్లు & బ్యాటరీలు*\n\nమీ కోసం అఫీషియల్ డిజిటల్ క్యాటలాగ్ లింక్:\n👉 ${url}\n\n🏷️ *డైనమిక్ డిస్కౌంట్లు & ధరల విశ్లేషణ (హబ్ హోల్‌సేల్ vs కస్టమర్ రిటైల్):*\n• గ్రాఫీన్ బ్యాటరీ 48V 32Ah (9 నెలల వారంటీ):\n   - హబ్ హోల్‌సేల్: ₹12,000 (18% GST కలిపి)\n   - కస్టమర్ రిటైల్: ₹14,100 → *ఆదా: ₹2,100 (15% తగ్గింపు)*\n• LFP లిథియం బ్యాటరీ 48V 30Ah (2+1 సం. వారంటీ, AIS-156):\n   - హబ్ హోల్‌సేల్: ₹18,800 (18% GST కలిపి)\n   - కస్టమర్ రిటైల్: ₹22,100 → *ఆదా: ₹3,300 (15% తగ్గింపు)*\n• ఫాస్ట్ ఛార్జర్ 48V (9 నెలల వారంటీ): హబ్ ₹1,500 | రిటైల్ ₹1,575\n• కంట్రోలర్లు & BMS స్పేర్స్: 20% నుండి 29% వరకు డైనమిక్ మార్జిన్!\n\n🛒 *EV స్పేర్స్ ఈ-కామ్ మార్కెట్‌ప్లేస్‌లో ఆర్డర్ చేయండి:*\n👉 http://localhost:5001/ecom?segment=ev-spares&category=spares\n\n24 గంటల్లో దేశవ్యాప్త డెలివరీ & అధికారిక GST ఇన్వాయిసింగ్.`,
      en: (cName, url) => `Namaskaram ${cName}! 🙏\n\n⚡ *MyntReal & VGK4U — Genuine EV Spares, Chargers & Batteries*\n\nHere is your official EV Spares & Battery Systems Digital Catalog:\n👉 ${url}\n\n🏷️ *Dynamic Discount & Cost Breakdown (Hub Wholesale vs Customer Retail):*\n• *Graphene Battery 48V 32Ah (9 Mo. Warranty):*\n   - Hub Wholesale: ₹12,000 (Incl. 18% GST)\n   - Customer Retail: ₹14,100 → *Save ₹2,100 (15% Margin)*\n• *LFP Lithium Battery 48V 30Ah (2+1 Yr. Warranty, AIS-156):*\n   - Hub Wholesale: ₹18,800 (Incl. 18% GST)\n   - Customer Retail: ₹22,100 → *Save ₹3,300 (15% Margin)*\n• *Smart Fast Charger 48V (9 Mo. Warranty):* Hub ₹1,500 | Retail ₹1,575\n• *Controllers & BMS Spares:* 20% to 29% dynamic wholesale margin!\n\n🛒 *Order Online on EV Spares E-Com Marketplace:*\n👉 http://localhost:5001/ecom?segment=ev-spares&category=spares\n\nImmediate 24-Hour Pan-India Dispatch | Full GST Invoicing.`,
      hi: (cName, url) => `नमस्ते ${cName} जी! 🙏\n\nMyntReal जेन्युइन ईवी स्पेयर पार्ट्स, चार्जर्स और बैटरी डिजिटल कैटलॉग लिंक यहाँ देखें:\n👉 ${url}\n\n⚙️ मुख्य उत्पाद एवं डायनामिक डिस्काउंट:\n• 15% से 25% तक की थोक (B2B) छूट\n• ग्रैफीन एवं LFP बैटरी पैक्स (9 माह से 3 साल वारंटी)\n• स्मार्ट बीएमएस एवं फास्ट चार्जर्स\n\nई-कॉमर्स पर ऑर्डर करने के लिए: http://localhost:5001/ecom?segment=ev-spares&category=spares`,
      ta: (cName, url) => `வணக்கம் ${cName}! 🙏\n\nMyntReal ஈவி உதிரிபாகங்கள், சார்ஜர்கள் & பேட்டரி டிஜிட்டல் கேட்லாக் லிங்க்:\n👉 ${url}\n\n15% முதல் 25% வரை தள்ளுபடி விலையில் ஈவி உதிரிபாகங்கள்!\nஇ-காமர்ஸ் மூலம் ஆர்டர் செய்ய: http://localhost:5001/ecom?segment=ev-spares&category=spares`
    }
  },
  etc_training: {
    name: 'ETC EV Technician Certifications',
    btnLabel: 'ETC Training',
    segmentSlug: 'etc',
    catalogSlug: 'etc-renewable-certifications',
    desc: 'Sends ETC Training catalog: 1-week EV certification at Govt. Poly Pendurthi, ₹10,000 scholarship discount.',
    messages: {
      te: (cName, url) => `నమస్కారం ${cName} గారు! 🙏\n\nEVolution Training Centre (ETC) ప్రొఫెషనల్ EV సర్టిఫికేషన్ డిజిటల్ క్యాటలాగ్ లింక్ ఇక్కడ చూడవచ్చు:\n👉 ${url}\n\n🎓 కోర్సు విశేషాలు:\n• 1-వారం ప్రాక్టికల్ EV టెక్నీషియన్ & ఎంటర్‌ప్రెన్యూర్‌షిప్ ప్రోగ్రామ్\n• Govt. Polytechnic College, Pendurthi లో ప్రత్యక్ష ప్రాక్టికల్ ల్యాబ్స్\n• BLDC మోటార్లు, బ్యాటరీ ప్యాక్ అసెంబ్లీ & BMS డయాగ్నోస్టిక్స్ లో శిక్షణ\n• ఫీజు ₹19,999 కి బదులుగా ₹10,000 స్కాలర్‌షిప్‌తో కేవలం ₹9,999 మాత్రమే!\n• 100% ప్లేస్‌మెంట్ అసిస్టెన్స్ & సర్వీస్ సెంటర్ బిజినెస్ గైడెన్స్\n\nపై లింక్ క్లిక్ చేసి సిలబస్ మరియు తదుపరి బ్యాచ్ వివరాలు చూడండి.`,
      en: (cName, url) => `Namaskaram ${cName}! 🙏\n\nHere is your official MyntReal EVolution Training Centre (ETC) Professional EV Certifications Digital Catalog link:\n👉 ${url}\n\n🎓 Certification Highlights:\n• 1-Week Intensive Hands-on EV Technician & Entrepreneurship Certification\n• Conducted at Govt. Polytechnic College, Pendurthi with live lab equipment\n• Deep training on BLDC motors, Lithium battery pack assembly & BMS debugging\n• Standard Fee ₹19,999 discounted by ₹10,000 Scholarship — Final Fee ₹9,999 only!\n• 100% Career placement assistance & EV service franchise support\n\nClick the link above to view curriculum, batch dates & reserve your seat.`,
      hi: (cName, url) => `नमस्ते ${cName} जी! 🙏\n\nEVolution Training Centre (ETC) प्रोफेशनल ईवी सर्टिफिकेशन डिजिटल कैटलॉग लिंक यहाँ देखें:\n👉 ${url}\n\n🎓 कोर्स की मुख्य विशेषताएं:\n• 1-सप्ताह का हैंड्स-ऑन ईवी तकनीशियन एवं उद्यमिता प्रमाणन\n• Govt. Polytechnic College, Pendurthi में व्यावहारिक प्रयोगशाला प्रशिक्षण\n• BLDC मोटर्स, लिथियम बैटरी पैक असेंबली और BMS डायग्नोस्टिक्स में महारत\n• ₹19,999 फीस पर ₹10,000 स्कॉलरशिप छूट — केवल ₹9,999!\n• 100% जॉब प्लेसमेंट सहायता एवं ईवी सर्विस सेंटर शुरू करने हेतु मार्गदर्शन\n\nकृपया ऊपर दिए गए लिंक पर क्लिक करके बैच डेट्स और सीट रिजर्व करें।`,
      ta: (cName, url) => `வணக்கம் ${cName}! 🙏\n\nEVolution Training Centre (ETC) தொழில்முறை ஈவி சான்றிதழ் டிஜிட்டல் கேட்லாக் லிங்க்:\n👉 ${url}\n\n🎓 பாடப்பிரிவின் சிறப்பம்சங்கள்:\n• 1 வார தீவிர செய்முறை ஈவி தொழில்நுட்ப வல்லுநர் பயிற்சி\n• அரசு பாலிடெக்னிக் கல்லூரி, பெந்துர்த்தியில் நேரடி பயிற்சி கூடங்கள்\n• BLDC மோட்டார், லித்தியம் பேட்டரி மற்றும் BMS பழுதுபார்ப்பு பயிற்சி\n• ₹19,999 கட்டணத்தில் ₹10,000 கல்வி உதவித்தொகை — கட்டணம் ₹9,999 மட்டுமே!\n• 100% வேலைவாய்ப்பு உதவி & தொழில் தொடங்க ஆதரவு\n\nமேலே உள்ள இணைப்பைக் கிளிக் செய்து பாடத்திட்டம் மற்றும் சேர்க்கை விவரங்களை அறிக.`
    }
  },
  insurance: {
    name: 'Comprehensive Insurance Advisory',
    btnLabel: 'Insurance',
    segmentSlug: 'insurance',
    catalogSlug: 'comprehensive-insurance-advisory',
    desc: 'Sends Insurance catalog with complete risk protection for EV fleets, solar rooftop plants, health & life.',
    messages: {
      te: (cName, url) => `నమస్కారం ${cName} గారు! 🙏\n\n🛡️ *VGK Care — 360° సమగ్ర బీమా & రిస్క్ ప్రొటెక్షన్*\n\nమీ కోసం అధికారిక ఇన్సూరెన్స్ అడ్వైజరీ డిజిటల్ క్యాటలాగ్ లింక్:\n👉 ${url}\n\n✨ *ముఖ్య బీమా రంగాలు & ప్రయోజనాలు:*\n• *ఈవీ మోటార్ & బ్యాటరీ రీప్లేస్‌మెంట్ కవర్:* లిథియం బ్యాటరీ డ్యామేజ్, వాటర్ ఇన్‌గ్రెస్ & జీరో-డిప్రిసియేషన్ ప్రొటెక్షన్\n• *సోలార్ రూఫ్‌టాప్ EPC ఆల్-రిస్క్ ఇన్సూరెన్స్:* తుఫాను, వర్షం, పిడుగుపాటు & జనరేషన్ లాస్ నష్టపరిహారం\n• *ఫ్యామిలీ క్యాష్‌లెస్‌ హెల్త్ ఇన్సూరెన్స్:* 4,500+ నెట్‌వర్క్ హాస్పిటల్స్ & నో రూమ్ రెంట్ క్యాపింగ్\n• *కమర్షియల్ & ఫ్యాక్టరీ లయబిలిటీ:* అగ్నిప్రమాదాలు, దొంగతనం & పబ్లిక్ లయబిలిటీ షీల్డ్\n• *98.6% క్లెయిమ్ సెటిల్‌మెంట్ రేషియో* & తక్షణ డిజిటల్ స్పాట్ ఇన్సూరెన్స్ జారీ\n\nపై లింక్ ద్వారా ప్రీమియం కాలిక్యులేట్ చేసుకోండి మరియు తక్షణ పాలసీ పొందండి.`,
      en: (cName, url) => `Namaskaram ${cName}! 🙏\n\n🛡️ *VGK Care — 360° Comprehensive Insurance & Risk Protection*\n\nHere is your official VGK Care Insurance Advisory Digital Catalog link:\n👉 ${url}\n\n✨ *Core Advisory & Coverage Highlights:*\n• *EV Motor & Battery Zero-Dep Cover:* Explicit protection for lithium battery replacement, water ingress & thermal runaway\n• *Solar Rooftop EPC All-Risk Policy:* Protects against cyclones, storm damage & generation loss downtime\n• *Family Cashless Health Plans:* 4,500+ cashless network hospitals with zero room-rent cap\n• *Commercial & Factory Liability:* Comprehensive fire, burglary, stock & business interruption cover\n• *98.6% Claim Settlement Ratio* with instant spot digital policy issuance\n\nClick the link above to calculate customized premiums and issue policies on spot.`,
      hi: (cName, url) => `नमस्ते ${cName} जी! 🙏\n\nMyntReal व्यापक बीमा सलाहकार (Insurance Advisory) डिजिटल कैटलॉग लिंक यहाँ देखें:\n👉 ${url}\n\n🛡️ बीमा सुरक्षा के मुख्य लाभ:\n• इलेक्ट्रिक वाहन (EV) और कमर्शियल फ्लीट विशेष बीमा\n• सोलर रूफटॉप प्लांट ऑल-रिस्क कवरेज\n• फैमिली हेल्थ एवं टर्म लाइफ इंश्योरेंस प्लान्स (कैशलेस सुविधा)\n• व्यापार और कमर्शियल प्रॉपर्टी प्रोटेक्शन\n• त्वरित क्लेम निपटान सहायता\n\nकृपया ऊपर दिए गए लिंक पर क्लिक करके बीमा योजनाओं की तुलना करें और कोटेशन पाएं।`,
      ta: (cName, url) => `வணக்கம் ${cName}! 🙏\n\nMyntReal விரிவான காப்பீட்டு ஆலோசனை (Insurance Advisory) டிஜிட்டல் கேட்லாக் லிங்க்:\n👉 ${url}\n\n🛡️ காப்பீட்டு சிறப்பம்சங்கள்:\n• எலக்ட்ரிக் வாகனங்கள் மற்றும் வணிக கடற்படைக்கான சிறப்பு காப்பீடு\n• சோலார் ஆலைக்கான முழுமையான இடர் பாதுகாப்பு\n• விரிவான மருத்துவ & ஆயுள் காப்பீட்டு திட்டங்கள்\n• உடனடி க்ளைம் தீர்வு உதவி\n\nமேலே உள்ள இணைப்பைக் கிளிக் செய்து பாலிசி விவரங்களை அறிந்து உடனடி கொட்டேஷன் பெறுங்கள்.`
    }
  },
  industrial_hub: {
    name: 'MyntReal Hub (5-in-1 Franchise)',
    btnLabel: 'MyntReal Hub',
    segmentSlug: 'industrial-hub',
    catalogSlug: 'industrial-hub-franchise',
    desc: 'Sends MyntReal Hub catalog: 5-in-1 investor franchise (EV, Solar, Insurance, Real Estate & Training) with ₹12–15L investment & 140% ROI.',
    messages: {
      te: (cName, url) => `నమస్కారం ${cName} గారు! 🙏\n\nMyntReal Hub (5-in-1 ఇన్వెస్టర్ ఫ్రాంచైజ్) అధికారిక డిజిటల్ క్యాటలాగ్ లింక్:\n👉 ${url}\n\n🏢 ఒకే హబ్ — 5 లాభదాయక వ్యాపార మార్గాలు:\n• మంత్ర ఈవీ షోరూమ్ & స్పేర్స్ డిపో (యూనిట్‌కు ₹7,000 మార్జిన్)\n• హర్ ఘర్ సోలార్ రూఫ్‌టాప్ EPC (₹78,000 సబ్సిడీ & ప్రాజెక్ట్‌కు ₹20,000 మార్జిన్)\n• VGK కేర్ ఇన్సూరెన్స్ అడ్వైజరీ (40+ ఇన్సూరర్లు, పాలసీకి ₹3,000 మార్జిన్)\n• VGK రియల్ డ్రీమ్స్ టౌన్‌షిప్స్ & విల్లాస్ బ్రోకరేజ్\n• EVolution ట్రైనింగ్ సెంటర్ (గవర్నమెంట్ పాలిటెక్నిక్ కాలేజ్ పార్టనర్)\n\n💼 పెట్టుబడి: ₹12–15 లక్షలు | బ్రేక్-ఈవెన్: 6-9 నెలలు | వార్షిక నికర ఆదాయం: ₹19.8 లక్షలు+\n🎁 ఫ్రాంచైజీతో పాటు కంప్యూటర్, 43" స్మార్ట్ టీవీ, కలర్ ప్రింటర్, షోరూమ్ బ్రాండింగ్ & 12 నెలల లీడ్ సపోర్ట్ ఉచితం!\n\nపై లింక్ క్లిక్ చేసి పూర్తి ప్రాస్పెక్టస్, ROI మోడల్ & వివరాలు చూడగలరు.`,
      en: (cName, url) => `Namaskaram ${cName}! 🙏\n\nHere is your official MyntReal Hub (5-in-1 Investor Franchise) Digital Catalog link:\n👉 ${url}\n\n🏢 One Hub — 5 High-Demand Business Streams:\n• Manthra EV Dealership & Spares (₹7,000 / unit margin)\n• Har Ghar Solar EPC (₹78,000 DBT subsidy & ₹20,000 / system margin)\n• VGK Care Insurance Advisory (40+ Insurers, ₹3,000 / policy margin)\n• VGK Real Dreams Townships & Luxury Villas (High-ticket brokerage)\n• EVolution Training Centre (Govt. Polytechnic College Campus)\n\n💼 Investment: ₹12 – 15 Lakhs | Break-even: 6–9 Months | Base Net: ₹19.80 Lakhs / yr\n🎁 Turnkey Setup: Business PC with MyntOS ERP, 43" Smart TV, Color Printer, Complete Showroom Branding & 12 Months Lead Support included!\n\nClick the link above to review complete deliverables, financial models & territory rights.`,
      hi: (cName, url) => `नमस्ते ${cName} जी! 🙏\n\nMyntReal Hub (5-इन-1 इन्वेस्टर फ्रैंचाइज़) आधिकारिक डिजिटल कैटलॉग लिंक यहाँ देखें:\n👉 ${url}\n\n🏢 एक हब — 5 उच्च मुनाफे वाले व्यापार:\n• मंत्रा ईवी डीलरशिप एवं स्पेयर पार्ट्स (₹7,000 प्रति वाहन मार्जिन)\n• हर घर सोलर रूफटॉप ईपीसी (₹78,000 सब्सिडी एवं ₹20,000 प्रति सिस्टम मार्जिन)\n• वीजीके केयर बीमा सलाहकार (40+ बीमा कंपनियाँ, ₹3,000 प्रति पॉलिसी मार्जिन)\n• वीजीके रियल ड्रीम्स टाउनशिप एवं विला ब्रोकरेज\n• ईवीोल्यूशन ट्रेनिंग सेंटर (गवर्नमेंट पॉलिटेक्निक कॉलेज पार्टनर)\n\n💼 निवेश: ₹12–15 लाख | ब्रेक-ईवन: 6–9 महीने | अनुमानित शुद्ध वार्षिक आय: ₹19.8 लाख+\n🎁 टर्नकी सेटअप: बिजनेस पीसी, 43" स्मार्ट टीवी, कलर प्रिंटर, शोरूम ब्रांडिंग और 12 महीने का लीड सपोर्ट शामिल!\n\nकृपया ऊपर दिए गए लिंक पर क्लिक करके पूरी जानकारी और आरओआई मॉडल देखें।`,
      ta: (cName, url) => `வணக்கம் ${cName}! 🙏\n\nMyntReal Hub (5-இன்-1 முதலீட்டு ஃபிரான்சைஸ்) அதிகாரப்பூர்வ டிஜிட்டல் கேட்லாக் லிங்க்:\n👉 ${url}\n\n🏢 ஒரே மையம் — 5 லாபகரமான வணிக வழிகள்:\n• மாந்த்ரா இ-வாகன விற்பனை & உதிரிபாகங்கள் மையம்\n• ஹர் கர் சோலார் கூரை மின் உற்பத்தி EPC (₹78,000 மானியம்)\n• VGK கேர் விரிவான காப்பீட்டு ஆலோசனை (40+ நிறுவனங்கள்)\n• VGK ரியல் ட்ரீம்ஸ் நிலம் & சொத்து விற்பனை\n• EVolution தொழில்முறை இ-வாகன பயிற்சி மையம்\n\n💼 முதலீடு: ₹12–15 லட்சம் | முதலீடு மீட்பு: 6–9 மாதங்கள் | ஆண்டு நிகர வருமானம்: ₹19.80 லட்சம்+\n🎁 கணினி, 43" ஸ்மார்ட் டிவி, கலர் பிரிண்டர், பிராண்டிங் மற்றும் 12 மாத லீட் ஆதரவு முற்றிலும் இலவசம்!\n\nமுழு விவரங்களையும் நிதி மாதிரியையும் காண மேலே உள்ள இணைப்பைக் கிளிக் செய்க.`
    }
  },
  hub_pricing: {
    name: 'Hub Commercials & Pricing (24h)',
    btnLabel: 'Hub Pricing (24h)',
    segmentSlug: 'hub-pricing',
    catalogSlug: 'hub-ev-pricing',
    desc: 'Sends confidential MyntReal Hub EV & Solar Commercial Pricing catalog with wholesale costs, dealer margins & 24h auto-expiry security.',
    messages: {
      te: (cName, url) => `నమస్కారం ${cName} గారు! 🙏\n\nMyntReal Hub — గోప్యమైన EV & సోలార్ కమర్షియల్ ప్రైసింగ్ & డీలర్ మార్జిన్స్ క్యాటలాగ్ లింక్ (24 గంటలు మాత్రమే చెల్లుబాటు):\n👉 ${url}\n\n⚡ కమర్షియల్ ప్రైసింగ్ & మార్జిన్ వివరాలు:\n• 5 మోడల్స్ EV వాహనాల హోల్‌సేల్ ధరలు & 12% హబ్ మార్జిన్ (~₹7,200/వాహనం)\n• డైరెక్ట్ కస్టమర్ సేల్స్ పై +10.5% అదనపు VGK4U కమిషన్ (మొత్తం 22.5% మార్జిన్)\n• గ్రాఫేన్ & LFP బ్యాటరీలు మరియు ఫాస్ట్ ఛార్జర్ల విడి భాగాల ధరల పట్టిక\n• సోలార్ EPC 1kW–10kW మాతృక: ₹1,99,999 సిస్టమ్‌పై ₹7,000 షోరూమ్ + ₹13,000 డైరెక్ట్ మార్జిన్\n• 3-దశల యూనిట్ ఎకనామిక్స్ & లైవ్ డైరెక్ట్ సేల్స్ ROI సిమ్యులేటర్\n\n⚠️ గమనిక: ఈ లింక్ కేవలం 24 గంటలు మాత్రమే యాక్టివ్‌గా ఉంటుంది.\n\nపై లింక్ క్లిక్ చేసి పూర్తి హోల్‌సేల్ కాస్ట్ షీట్ & ROI వివరాలు వెంటనే చూడగలరు.`,
      en: (cName, url) => `Namaskaram ${cName}! 🙏\n\nHere is your Confidential MyntReal Hub — EV & Solar Commercial Pricing & Dealer Margins Prospectus (Strictly Valid for 24 Hours):\n👉 ${url}\n\n⚡ Commercial Highlights:\n• OEM Wholesale Central Pricing & 12% Hub Dealer Margin (~₹7,200 avg/vehicle)\n• Direct Customer Sale: +10.5% VGK4U Bonus (Total 22.5% combined spread)\n• Standalone Graphene & LFP Batteries + Smart Fast Chargers Cost Matrix\n• Solar EPC 1kW–10kW: ₹1,99,999 Flagship gives ₹7,000 Showroom + ₹13,000 Direct Margin\n• 3-Scenario Financial Viability & Interactive Investor ROI Simulator\n\n⚠️ Note: This confidential link expires automatically in 24 hours.\n\nClick the link above to review wholesale cost sheets & calculate your net returns.`,
      hi: (cName, url) => `नमस्ते ${cName} जी! 🙏\n\nMyntReal Hub — गोपनीय EV और सोलर कमर्शियल प्राइसिंग एवं डीलर मार्जिन कैटलॉग लिंक (केवल 24 घंटे मान्य):\n👉 ${url}\n\n⚡ मुख्य व्यावसायिक विवरण:\n• 5 मॉडल्स EV वाहनों की थोक खरीद लागत और 12% हब डीलर मार्जिन\n• डायरेक्ट सेल पर +10.5% अतिरिक्त VGK4U कमीशन (कुल 22.5% मार्जिन)\n• ग्रैफीन एवं LFP बैटरियां और फास्ट चार्जर कंपोनेंट लागत सूची\n• सोलर EPC 1kW–10kW: ₹1,99,999 प्लांट पर ₹7,000 शोरूम + ₹13,000 डायरेक्ट मार्जिन\n• 3-सिनेरियो यूनिट इकोनॉमिक्स और लाइव ROI सिम्युलेटर\n\n⚠️ ध्यान दें: यह लिंक केवल 24 घंटे के लिए सक्रिय है।\n\nकृपया तुरंत ऊपर दिए गए लिंक पर क्लिक करके पूरी कॉस्ट शीट देखें।`,
      ta: (cName, url) => `வணக்கம் ${cName}! 🙏\n\nMyntReal Hub — ரகசியமான EV & சோலார் வணிக விலை & டீலர் மார்ஜின் கேட்லாக் லிங்க் (24 மணிநேரம் மட்டுமே செல்லுபடியாகும்):\n👉 ${url}\n\n⚡ வணிக சிறப்பம்சங்கள்:\n• 5 மாடல் மின்சார வாகன மொத்த விலை & 12% ஹப் டீலர் மார்ஜின்\n• நேரடி விற்பனையில் +10.5% கூடுதல் VGK4U கமிஷன் (மொத்தம் 22.5% லாபம்)\n• கிராபீன் & LFP பேட்டரிகள் மற்றும் பாஸ்ட் சார்ஜர் உதிரிபாகங்கள் விலை பட்டியல்\n• சோலார் EPC 1kW–10kW: ₹1,99,999 அமைப்பில் ₹7,000 ஷோரூம் + ₹13,000 நேரடி மார்ஜின்\n• 3-நிலை நிதி சாத்தியக்கூறு ஆய்வு & நேரடி ROI கால்குலேட்டர்\n\n⚠️ குறிப்பு: இந்த ரகசிய இணைப்பு 24 மணிநேரத்திற்கு மட்டுமே செல்லுபடியாகும்.\n\nமுழு விலை மற்றும் வருவாய் விவரங்களை அறிய மேலே உள்ள இணைப்பை கிளிக் செய்யவும்.`
    }
  }
};

class UnifiedWAModal {
  private modalEl: HTMLElement | null = null;
  private currentOptions: WAModalOptions | null = null;
  private activeMode: 'scanned' | 'meta_api' = 'scanned';

  private selectedCatalogKey: string = 'solar';
  private selectedCatalogLang: string = 'te';

  private allCanonicalTemplates: any[] = [];
  private canonicalTemplates: any[] = [];
  private selectedCanonicalBody: string = '';

  private getSenderSignature(): string {
    const authState = authService.getAuthState();
    const user: any = authState.user || {};
    const fullName = user.full_name || user.name || `${user.first_name || ''} ${user.last_name || ''}`.trim() || 'Staff';
    let ext = user.extension || user.ext || (typeof window !== 'undefined' ? (window as any).__STAFF_EXTENSION__ : null);
    if (!ext && user.emp_code) {
      const m = String(user.emp_code).match(/(\d{2,4})$/);
      if (m) ext = m[1].replace(/^0+/, '') || m[1];
    }
    if (ext && String(ext).trim() && !['none', 'null', 'undefined', 'n/a'].includes(String(ext).trim().toLowerCase())) {
      return `\n\nRegards,\n${fullName}\n📞 +91 85858 52738 | +91 8897797667\nExt: ${String(ext).trim()}`;
    }
    return `\n\nRegards,\n${fullName}\n📞 +91 85858 52738 | +91 8897797667`;
  }

  private getVerticalQuickMessage(action: 'thanks_connecting' | 'trying_to_reach'): string {
    const cName = (this.currentOptions?.name || 'Customer').trim();
    const ctx = (this.currentOptions?.context || '').toLowerCase();
    
    let vertical: 'solar' | 'real_estate' | 'insurance' | 'ev' | 'etc' | 'general' = 'general';
    if (ctx.includes('solar')) {
      vertical = 'solar';
    } else if (ctx.includes('real') || ctx.includes('property') || ctx.includes('estate')) {
      vertical = 'real_estate';
    } else if (ctx.includes('insur') || ctx.includes('care')) {
      vertical = 'insurance';
    } else if (ctx.includes('ev') || ctx.includes('spare') || ctx.includes('zynova') || ctx.includes('vehicle')) {
      vertical = 'ev';
    } else if (ctx.includes('etc') || ctx.includes('train') || ctx.includes('skill')) {
      vertical = 'etc';
    }

    if (action === 'thanks_connecting') {
      switch (vertical) {
        case 'solar':
          return `నమస్కారం ${cName} గారు! 🙏 MyntReal Solar Rooftop గురించి మాతో మాట్లాడినందుకు ధన్యవాదాలు. మీ ఇంటి లేదా కమర్షియల్ కరెంట్ బిల్లును 90% వరకు తగ్గించుకుంటూ, Government Subsidy పొందే పూర్తి వివరాలు & Customized Solar Quotation త్వరలోనే మా సోలార్ ఎక్స్‌పర్ట్ మీకు షేర్ చేస్తారు. ఏవైనా డౌట్స్ ఉంటే దయచేసి ఇక్కడ మెసేజ్ చేయండి.`;
        case 'real_estate':
          return `నమస్కారం ${cName} గారు! 🙏 MyntReal Properties తో కనెక్ట్ అయినందుకు ధన్యవాదాలు. మీ బడ్జెట్ మరియు రిక్వైర్‌మెంట్‌కు తగినట్లుగా బెస్ట్ వెరిఫైడ్ ఓపెన్ ప్లాట్స్, గేటెడ్ కమ్యూనిటీ విల్లాస్ మరియు అపార్ట్‌మెంట్స్ వివరాలను మా ప్రాపర్టీ స్పెషలిస్ట్ త్వరలోనే మీకు షేర్ చేస్తారు. సైట్ విజిట్ కోసం ఎప్పుడైనా సంప్రదించవచ్చు.`;
        case 'insurance':
          return `నమస్కారం ${cName} గారు! 🙏 MyntReal Insurance & Protection తో మాట్లాడినందుకు ధన్యవాదాలు. మీకు మరియు మీ కుటుంబానికి సరిపోయే బెస్ట్ Health, Life మరియు General Insurance పాలసీ కొటేషన్లను మా ఇన్సూరెన్స్ అడ్వైజర్ మీకు పంపిస్తారు. పూర్తి క్లెయిమ్ సపోర్ట్ మా బాధ్యత.`;
        case 'ev':
          return `నమస్కారం ${cName} గారు! 🙏 MyntReal EV & Spares గురించి మాతో కనెక్ట్ అయినందుకు ధన్యవాదాలు. లేటెస్ట్ ఎలక్ట్రిక్ వెహికల్ మోడల్స్, రేంజ్, బ్యాటరీ వారంటీ, ఫైనాన్స్ ఆప్షన్స్ మరియు టెస్ట్ రైడ్ వివరాలను మా ఈవీ స్పెషలిస్ట్ మీకు త్వరలోనే అందిస్తారు.`;
        case 'etc':
          return `నమస్కారం ${cName} గారు! 🙏 MyntReal ETC Skill Training ప్రోగ్రామ్స్ గురించి మాట్లాడినందుకు ధన్యవాదాలు. మీ కెరీర్ గ్రోత్‌కు అవసరమైన సర్టిఫైడ్ ట్రైనింగ్ కోర్సులు, బ్యాచ్ టైమింగ్స్ మరియు జాబ్ అసిస్టెన్స్ వివరాలు మా కోఆర్డినేటర్ మీకు పంపిస్తారు.`;
        default:
          return `నమస్కారం ${cName} గారు! 🙏 MyntReal తో కనెక్ట్ అయినందుకు చాలా ధన్యవాదాలు. మా అన్ని ప్రీమియర్ సర్వీసెస్ మీ సేవలో అందుబాటులో ఉన్నాయి:\n☀️ Solar Rooftop & Renewable Energy (కరెంట్ బిల్లు 90% వరకు ఆదా & Govt సబ్సిడీ)\n🏡 Real Estate & Premier Properties (ఓపెన్ ప్లాట్స్, విల్లాస్ & అపార్ట్‌మెంట్స్)\n🛡️ Insurance & Protection Solutions (హెల్త్, లైఫ్ & జనరల్ పాలసీలు)\n🛵 EV Vehicles & Genuine Spares (ఎకో-ఫ్రెండ్లీ ఎలక్ట్రిక్ బైక్స్ & సర్వీస్)\n🎓 ETC Skill Training & Career Certifications (ఉద్యోగ నైపుణ్య శిక్షణ)\n\nమా Relationship Manager మీకు పూర్తి వివరాలు అందిస్తారు. మీకు ఏ సమాచారం కావాలన్నా దయచేసి ఇక్కడ మెసేజ్ చేయగలరు!`;
      }
    } else {
      switch (vertical) {
        case 'solar':
          return `నమస్కారం ${cName} గారు! 📞 మీ Solar Rooftop ఎంక్వైరీ కోసం MyntReal నుండి ఇప్పుడే కాల్ చేశాము, కానీ కాల్ కలవలేదు. మీరు ఫ్రీగా ఉన్నప్పుడు దయచేసి ఈ మెసేజ్‌కి రిప్లై ఇవ్వండి లేదా కాల్ బ్యాక్ చేయండి. సోలార్ సబ్సిడీ మరియు సేవింగ్స్ వివరాలు తెలియజేస్తాము.`;
        case 'real_estate':
          return `నమస్కారం ${cName} గారు! 📞 మీ Real Estate ప్రాపర్టీ ఎంక్వైరీ గురించి MyntReal నుండి కాల్ చేశాము, మాట్లాడటం కుదరలేదు. మీకు అనుకూలమైన టైమ్‌లో దయచేసి రిప్లై ఇవ్వండి లేదా కాల్ చేయండి. మీ రిక్వైర్‌మెంట్‌కు సరిపడే బెస్ట్ ప్రాపర్టీ ఆప్షన్స్ మీకు పంపిస్తాము.`;
        case 'insurance':
          return `నమస్కారం ${cName} గారు! 📞 మీ Insurance ఎంక్వైరీ గురించి MyntReal నుండి కాల్ చేశాము, కాల్ కలవలేదు. మీకు ఫ్రీ టైమ్ ఉన్నప్పుడు దయచేసి ఇక్కడ రిప్లై ఇవ్వండి. మీకు అనువైన బెస్ట్ ఇన్సూరెన్స్ ప్లాన్స్ వివరాలు చర్చిద్దాం.`;
        case 'ev':
          return `నమస్కారం ${cName} గారు! 📞 మీ EV Vehicle & Spares ఎంక్వైరీ కోసం MyntReal నుండి కాల్ చేశాము, మాట్లాడటం వీలుపడలేదు. మీరు వీలైనప్పుడు రిప్లై ఇవ్వండి లేదా కాల్ చేయండి. టెస్ట్ రైడ్ మరియు మోడల్స్ వివరాలు మీకు తెలియజేస్తాము.`;
        case 'etc':
          return `నమస్కారం ${cName} గారు! 📞 మీ ETC Skill Training కోర్సు వివరాల కోసం MyntReal నుండి కాల్ చేశాము, కాల్ కనెక్ట్ అవ్వలేదు. మీరు ఫ్రీగా ఉన్నప్పుడు దయచేసి మెసేజ్ చేయండి. అప్‌కమింగ్ బ్యాచ్ టైమింగ్స్ మరియు ఫీజు వివరాలు చర్చిద్దాం.`;
        default:
          return `నమస్కారం ${cName} గారు! 📞 MyntReal నుండి మీతో మాట్లాడటానికి ఇప్పుడే కాల్ చేశాము, కానీ కాల్ కలవలేదు / మీరు బిజీగా ఉన్నట్లున్నారు. మేము మీకు క్రింది సర్వీసెస్‌లో ఉత్తమ సేవలు అందిస్తున్నాము:\n☀️ Solar Energy (సోలార్ రూఫ్‌టాప్ & సబ్సిడీ)\n🏡 Real Estate (వెరిఫైడ్ ప్రాపర్టీస్ & సైట్ విజిట్స్)\n🛡️ Insurance (హెల్త్ & లైఫ్ ఇన్సూరెన్స్)\n🛵 EV Vehicles & Spares (ఎలక్ట్రిక్ స్కూటర్లు & స్పేర్స్)\n🎓 ETC Skill Training (నైపుణ్య శిక్షణ & కెరీర్)\n\nమీకు అనుకూలమైన సమయంలో దయచేసి ఇక్కడ మెసేజ్ చేయండి లేదా కాల్ బ్యాక్ చేయగలరు!`;
      }
    }
  }

  private applyVerticalQuick(action: 'thanks_connecting' | 'trying_to_reach'): void {
    const text = this.getVerticalQuickMessage(action);
    const sig = this.getSenderSignature();
    const textEl = document.getElementById('uwaMessageText') as HTMLTextAreaElement;
    if (textEl) {
      textEl.value = text + sig;
      textEl.focus();
    }
  }

  private onDigitalCatalogSelect(catKey?: string): void {
    if (catKey && DIGITAL_CATALOGS[catKey]) {
      this.selectedCatalogKey = catKey;
    }
    const cat = DIGITAL_CATALOGS[this.selectedCatalogKey] || DIGITAL_CATALOGS.solar;
    const descEl = document.getElementById('uwaDigitalCatDesc');
    if (descEl) descEl.textContent = cat.desc;
    const btnLabelEl = document.getElementById('uwaDigitalCatBtnLabel');
    if (btnLabelEl) btnLabelEl.textContent = `Insert Personalized ${cat.btnLabel || cat.name} Catalog Link`;
  }

  private getDigitalCatalogMessage(catKey: string, lang: string): string {
    const cat = DIGITAL_CATALOGS[catKey] || DIGITAL_CATALOGS.solar;
    const cName = (this.currentOptions?.name || 'Customer').trim();
    const origin = (typeof window !== 'undefined' && window.location && window.location.origin && !window.location.origin.includes('localhost') && !window.location.origin.includes('capacitor')) ? window.location.origin : 'https://www.myntreal.com';
    let catalogUrl = `${origin}/catalog/${cat.segmentSlug}/${cat.catalogSlug}?lang=${encodeURIComponent(lang || 'te')}`;
    if (catKey === 'hub_pricing' && !catalogUrl.includes('exp=')) {
      catalogUrl += `&exp=${Math.floor(Date.now() / 1000) + 86400}`;
    }

    const l = (lang || 'te').toLowerCase() as 'te' | 'en' | 'hi' | 'ta';
    const msgFn = cat.messages[l] || cat.messages.en;
    if (typeof msgFn === 'function') {
      return msgFn(cName, catalogUrl);
    }
    return `Namaskaram ${cName}! Here is your catalog link:\n👉 ${catalogUrl}`;
  }

  private applyDigitalCatalog(lang?: string): void {
    if (lang) {
      this.selectedCatalogLang = lang;
      const pills = this.modalEl?.querySelectorAll('.uwa-cat-lang-btn');
      pills?.forEach(b => {
        const isThis = (b as HTMLElement).getAttribute('data-lang') === lang;
        (b as HTMLElement).style.background = isThis ? '#16a34a' : '#fff';
        (b as HTMLElement).style.color = isThis ? '#fff' : '#334155';
        (b as HTMLElement).style.borderColor = isThis ? '#16a34a' : '#cbd5e1';
        (b as HTMLElement).style.fontWeight = isThis ? '700' : '600';
      });
    }

    const sel = document.getElementById('uwaDigitalCatSel') as HTMLSelectElement;
    if (sel && sel.value) {
      this.selectedCatalogKey = sel.value;
    }

    const msg = this.getDigitalCatalogMessage(this.selectedCatalogKey, this.selectedCatalogLang);
    const sig = this.getSenderSignature();
    const textEl = document.getElementById('uwaMessageText') as HTMLTextAreaElement;
    if (textEl) {
      textEl.value = msg + sig;
      textEl.focus();
    }
  }

  private detectCatalogKey(): string {
    const ctx = (this.currentOptions?.context || '').toLowerCase();
    const seg = (this.currentOptions?.segment || '').toLowerCase();
    if (ctx.includes('solar') || seg === 'solar') return 'solar';
    if (ctx.includes('real') || ctx.includes('property') || ctx.includes('estate') || seg === 'myntreal_real') return 'real_estate';
    if (ctx.includes('spare') || seg === 'ev_spares') return 'ev_spares';
    if (ctx.includes('cargo') || ctx.includes('fleet') || ctx.includes('b2b') || seg === 'ev_b2b') return 'ev_b2b';
    if (ctx.includes('ev') || ctx.includes('zynova') || ctx.includes('vehicle') || seg === 'ev_b2c') return 'ev_b2c';
    if (ctx.includes('train') || ctx.includes('skill') || ctx.includes('etc') || seg === 'etc_training') return 'etc_training';
    if (ctx.includes('insur') || ctx.includes('policy') || ctx.includes('care')) return 'insurance';
    if (ctx.includes('pricing') || ctx.includes('margin') || ctx.includes('commercial') || seg === 'hub_pricing') return 'hub_pricing';
    if (ctx.includes('hub') || ctx.includes('franchise')) return 'industrial_hub';
    return 'solar';
  }

  private async loadCanonicalTemplates(selectId?: string | number): Promise<void> {
    const sel = document.getElementById('uwaCanonicalTpl') as HTMLSelectElement;
    const noTpl = document.getElementById('uwaNoTplNotice');
    if (!sel) return;

    sel.innerHTML = '<option value="">— Loading templates… —</option>';
    if (noTpl) noTpl.style.display = 'none';

    const mode = this.activeMode === 'scanned' ? 'scanned' : 'company';
    let url = `/whatsapp-config/templates?mode=${encodeURIComponent(mode)}`;

    try {
      const res = await apiService.get<any>(url);
      const list = res?.templates || res?.data || res || [];
      this.allCanonicalTemplates = Array.isArray(list) ? list : [];
      this.filterCanonicalTemplates(selectId);
    } catch {
      sel.innerHTML = '<option value="">— Error loading templates —</option>';
    }
  }

  private filterCanonicalTemplates(selectId?: string | number): void {
    const sel = document.getElementById('uwaCanonicalTpl') as HTMLSelectElement;
    const noTpl = document.getElementById('uwaNoTplNotice');
    if (!sel) return;

    const segEl = document.getElementById('uwaCanonicalSeg') as HTMLSelectElement;
    const catEl = document.getElementById('uwaCanonicalCat') as HTMLSelectElement;
    const searchEl = document.getElementById('uwaCanonicalSearch') as HTMLInputElement;

    const seg = (segEl?.value || '').toLowerCase().trim();
    const cat = (catEl?.value || '').toUpperCase().trim();
    const query = (searchEl?.value || '').toLowerCase().trim();

    let filtered = this.allCanonicalTemplates || [];

    if (seg) {
      filtered = filtered.filter(t => (t.segment || '').toLowerCase() === seg);
    }
    if (cat) {
      filtered = filtered.filter(t => (t.category || '').toUpperCase() === cat);
    }
    if (query) {
      filtered = filtered.filter(t => {
        const name = (t.template_name || t.name || '').toLowerCase();
        const body = (t.body_text || t.content || t.body || '').toLowerCase();
        const slug = (t.slug || '').toLowerCase();
        return name.includes(query) || body.includes(query) || slug.includes(query);
      });
    }

    this.canonicalTemplates = filtered;

    if (!filtered.length) {
      sel.innerHTML = `
        <option value="">— No templates found for this filter —</option>
        <option value="__create_new__" style="color:#16a34a; font-weight:700;">➕ Create / Add Template for this Segment...</option>
      `;
      if (noTpl) noTpl.style.display = 'block';
      this.onCanonicalTplChange();
      return;
    }

    if (noTpl) noTpl.style.display = 'none';

    let optHtml = `<option value="">— Select template (${filtered.length} available) —</option>`;
    optHtml += `<option value="__create_new__" style="color:#16a34a; font-weight:700;">➕ Create / Add Template for this Segment...</option>`;

    filtered.forEach(t => {
      const segLabel = t.segment ? `[${t.segment}] ` : '';
      optHtml += `<option value="${t.id}">${segLabel}${this.escapeHtml(t.template_name || t.name || 'Template #' + t.id)} (${t.category || 'MARKETING'})</option>`;
    });

    sel.innerHTML = optHtml;

    if (selectId) {
      sel.value = String(selectId);
      this.onCanonicalTplChange();
    }
  }

  private toggleAddTemplateCard(show?: boolean): void {
    const card = document.getElementById('uwaAddTplCard');
    if (!card) return;
    const isVisible = card.style.display !== 'none';
    const nextShow = (show !== undefined) ? show : !isVisible;
    card.style.display = nextShow ? 'block' : 'none';
    if (nextShow) {
      const curSeg = (document.getElementById('uwaCanonicalSeg') as HTMLSelectElement)?.value || this.detectSegment();
      const newSegEl = document.getElementById('uwaNewTplSeg') as HTMLSelectElement;
      if (newSegEl && curSeg) {
        newSegEl.value = curSeg;
      }
      document.getElementById('uwaNewTplName')?.focus();
    }
  }

  private async saveNewTemplate(): Promise<void> {
    const nameEl = document.getElementById('uwaNewTplName') as HTMLInputElement;
    const segEl = document.getElementById('uwaNewTplSeg') as HTMLSelectElement;
    const bodyEl = document.getElementById('uwaNewTplBody') as HTMLTextAreaElement;
    const saveBtn = document.getElementById('uwaSaveNewTplBtn') as HTMLButtonElement;

    const name = (nameEl?.value || '').trim();
    const seg = segEl?.value || 'general';
    const body = (bodyEl?.value || '').trim();

    if (!name) {
      this.showFeedback('Please enter a template name.', 'error');
      return;
    }
    if (!body) {
      this.showFeedback('Please enter the template message body.', 'error');
      return;
    }

    if (saveBtn) saveBtn.disabled = true;
    const slug = name.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 40);

    try {
      const res = await apiService.post<any>('/whatsapp-config/templates', {
        name: name,
        slug: slug,
        category: 'MARKETING',
        segment: seg,
        body_text: body,
        language: 'en',
        usage_scope: 'all'
      });

      if (res?.success) {
        this.showFeedback(`✅ Template "${name}" created & approved for WhatsApp API!`, 'success');
        this.toggleAddTemplateCard(false);
        if (nameEl) nameEl.value = '';
        if (bodyEl) bodyEl.value = '';

        const canonicalSeg = document.getElementById('uwaCanonicalSeg') as HTMLSelectElement;
        if (canonicalSeg) canonicalSeg.value = seg;

        const newId = res.template?.id || res.id || slug;
        await this.loadCanonicalTemplates(newId);
      } else {
        this.showFeedback(res?.error || 'Failed to create template', 'error');
      }
    } catch(err: any) {
      this.showFeedback(`Error creating template: ${err.message || 'Server error'}`, 'error');
    } finally {
      if (saveBtn) saveBtn.disabled = false;
    }
  }

  private detectSegment(): string {
    if (this.currentOptions?.segment) return this.currentOptions.segment;
    const ctx = (this.currentOptions?.context || '').toLowerCase();
    if (ctx.includes('solar')) return 'solar';
    if (ctx.includes('real') || ctx.includes('property') || ctx.includes('estate')) return 'myntreal_real';
    if (ctx.includes('spare')) return 'EV_SPARES';
    if (ctx.includes('ev') || ctx.includes('vehicle') || ctx.includes('zynova')) return 'ev_b2c';
    if (ctx.includes('train') || ctx.includes('skill') || ctx.includes('etc')) return 'etc_training';
    if (ctx.includes('partner')) return 'partner';
    if (ctx.includes('staff')) return 'staff';
    if (ctx.includes('vgk')) return 'vgk';
    return 'general';
  }

  private onCanonicalTplChange(): void {
    const sel = document.getElementById('uwaCanonicalTpl') as HTMLSelectElement;
    const varsWrap = document.getElementById('uwaCanonicalVarsWrap');
    const varsBox = document.getElementById('uwaCanonicalVarsBox');
    const tplId = sel?.value;

    if (tplId === '__create_new__') {
      this.toggleAddTemplateCard(true);
      sel.value = '';
      return;
    }

    if (!tplId) {
      if (varsWrap) varsWrap.style.display = 'none';
      if (varsBox) varsBox.innerHTML = '';
      return;
    }

    const tpl = this.canonicalTemplates.find(t => String(t.id) === String(tplId) || String(t.slug) === String(tplId));
    if (!tpl) return;

    this.selectedCanonicalBody = tpl.body_text || tpl.content || tpl.body || '';

    const matches = this.selectedCanonicalBody.match(/\{\{(\d+)\}\}/g) || [];
    const uniqueIndices: string[] = [];
    matches.forEach(m => {
      const idx = m.replace(/[\{\}]/g, '');
      if (!uniqueIndices.includes(idx)) uniqueIndices.push(idx);
    });
    uniqueIndices.sort((a, b) => Number(a) - Number(b));

    if (uniqueIndices.length && varsBox && varsWrap) {
      varsWrap.style.display = 'block';
      let html = '';
      uniqueIndices.forEach(idx => {
        const defaultVal = (idx === '1') ? (this.currentOptions?.name || '') : '';
        html += `
          <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
            <label style="font-size:11px; font-weight:700; width:28px; color:#475569;">#${idx}</label>
            <input type="text" class="uwa-canonical-var-inp" data-var-idx="${idx}" value="${this.escapeHtml(defaultVal)}" placeholder="Value for {{${idx}}}" style="flex:1; font-size:12px; border:1px solid #cbd5e1; border-radius:6px; padding:4px 8px;" />
          </div>
        `;
      });
      varsBox.innerHTML = html;

      varsBox.querySelectorAll('.uwa-canonical-var-inp').forEach(inp => {
        inp.addEventListener('input', () => this.buildCanonicalPreview());
      });
    } else {
      if (varsWrap) varsWrap.style.display = 'none';
      if (varsBox) varsBox.innerHTML = '';
    }

    this.buildCanonicalPreview();
  }

  private buildCanonicalPreview(): void {
    let text = this.selectedCanonicalBody || '';
    const matches = text.match(/\{\{(\d+)\}\}/g) || [];
    matches.forEach(m => {
      const idx = m.replace(/[\{\}]/g, '');
      const inp = document.querySelector(`.uwa-canonical-var-inp[data-var-idx="${idx}"]`) as HTMLInputElement;
      const val = inp?.value || `{{${idx}}}`;
      text = text.replace(new RegExp(`\\{\\{${idx}\\}\\}`, 'g'), val);
    });

    const sig = this.getSenderSignature();
    const textEl = document.getElementById('uwaMessageText') as HTMLTextAreaElement;
    if (textEl && text) {
      textEl.value = text + sig;
    }
  }

  open(options: WAModalOptions): void {
    this.currentOptions = options;
    this.activeMode = 'scanned';
    this.render();
  }

  close(): void {
    if (this.modalEl) {
      this.modalEl.remove();
      this.modalEl = null;
    }
  }

  private render(): void {
    this.close();

    if (!this.currentOptions) return;

    const { phone, name, context, defaultMessage } = this.currentOptions;
    const cleanPhone = (phone || '').replace(/\D/g, '').slice(-10);
    const signature = this.getSenderSignature();
    const initialText = (defaultMessage || this.getVerticalQuickMessage('thanks_connecting')) + signature;

    this.modalEl = document.createElement('div');
    this.modalEl.id = 'unifiedWAModal';
    this.modalEl.className = 'uwa-modal-backdrop';
    this.modalEl.innerHTML = `
      <div class="uwa-modal-sheet">
        <!-- Header -->
        <div class="uwa-header">
          <div class="uwa-header-info">
            <div class="uwa-badge-online">
              <span class="uwa-dot"></span> Common Number Connected
            </div>
            <h3 class="uwa-title"><i class="fab fa-whatsapp me-1"></i> Send WhatsApp</h3>
            <div class="uwa-recipient-sub">
              <strong>${this.escapeHtml(name || 'Customer')}</strong> · ${this.maskPhone(cleanPhone)}
              ${context ? `<span class="uwa-ctx-tag ms-1">${this.escapeHtml(context)}</span>` : ''}
            </div>
          </div>
          <button class="uwa-close-btn" id="uwaCloseBtn">&times;</button>
        </div>

        <!-- Mode Selector (Scanned WA vs Meta Cloud API) -->
        <div class="uwa-mode-bar">
          <button class="uwa-mode-btn ${this.activeMode === 'scanned' ? 'active' : ''}" id="uwaModeScannedBtn">
            <i class="fas fa-qrcode"></i>
            <div>
              <strong>📱 Scanned WhatsApp</strong>
              <small>Employee Account · Scanned</small>
            </div>
          </button>
          <button class="uwa-mode-btn ${this.activeMode === 'meta_api' ? 'active' : ''}" id="uwaModeMetaBtn">
            <i class="fas fa-building"></i>
            <div>
              <strong>🏢 Official WhatsApp</strong>
              <small>Meta Cloud API · Verified</small>
            </div>
          </button>
        </div>

        <!-- 1-Tap Vertical Quick Responses -->
        <div class="uwa-section-label">⚡ 1-Tap Quick Responses</div>
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px;">
          <button id="uwaQuickThanksBtn" type="button" style="background:#ecfdf5; border:1.5px solid #a7f3d0; color:#065f46; border-radius:10px; padding:8px 10px; font-size:12px; font-weight:700; cursor:pointer; text-align:left; display:flex; align-items:center; gap:6px;">
            <span style="font-size:16px;">🙏</span>
            <div>
              <div>Thanks for Connecting</div>
              <small style="font-size:9.5px; font-weight:normal; opacity:.8;">Service tailored</small>
            </div>
          </button>
          <button id="uwaQuickReachBtn" type="button" style="background:#fef3c7; border:1.5px solid #fde68a; color:#92400e; border-radius:10px; padding:8px 10px; font-size:12px; font-weight:700; cursor:pointer; text-align:left; display:flex; align-items:center; gap:6px;">
            <span style="font-size:16px;">📞</span>
            <div>
              <div>Trying to Reach</div>
              <small style="font-size:9.5px; font-weight:normal; opacity:.8;">Call missed / inquiry</small>
            </div>
          </button>
        </div>

        <!-- 1-Tap Digital Catalog Share -->
        <div class="uwa-section-label">📖 Send Digital Catalog</div>
        <div style="background:#f0fdf4; border:1.5px solid #86efac; border-radius:10px; padding:10px; margin-bottom:12px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; gap:6px; flex-wrap:wrap;">
            <div style="display:flex; align-items:center; gap:6px; flex:1; min-width:160px;">
              <i class="fas fa-book-open" style="color:#15803d; font-size:13px;"></i>
              <select id="uwaDigitalCatSel" style="flex:1; font-size:11px; font-weight:700; color:#166534; background:#fff; border:1.5px solid #86efac; border-radius:6px; padding:4px 6px; cursor:pointer; outline:none;">
                <option value="solar">☀️ Solar Rooftop &amp; EPC</option>
                <option value="industrial_hub">🏢 MyntReal Hub (5-in-1 Franchise)</option>
                <option value="hub_pricing">🏷️ Hub Commercials &amp; Pricing (24h)</option>
                <option value="ev_b2b">🚚 Commercial EV Fleet &amp; Cargo (B2B)</option>
                <option value="ev_b2c">⚡ Smart Electric 2-Wheelers (B2C)</option>
                <option value="ev_spares">⚙️ EV Spares, Chargers &amp; Batteries</option>
                <option value="etc_training">🎓 ETC EV Technician Certifications</option>
                <option value="real_estate">🏡 Premium Real Estate &amp; Townships</option>
                <option value="insurance">🛡️ Comprehensive Insurance Advisory</option>
              </select>
            </div>
            <div style="display:flex; gap:3px;" id="uwaDigitalCatLangPills">
              <button type="button" class="uwa-cat-lang-btn" data-lang="te" style="padding:2px 7px; border-radius:5px; border:1px solid #16a34a; background:#16a34a; color:#fff; font-size:10.5px; font-weight:700; cursor:pointer;">తెలుగు</button>
              <button type="button" class="uwa-cat-lang-btn" data-lang="en" style="padding:2px 7px; border-radius:5px; border:1px solid #cbd5e1; background:#fff; color:#334155; font-size:10.5px; font-weight:600; cursor:pointer;">EN</button>
              <button type="button" class="uwa-cat-lang-btn" data-lang="hi" style="padding:2px 7px; border-radius:5px; border:1px solid #cbd5e1; background:#fff; color:#334155; font-size:10.5px; font-weight:600; cursor:pointer;">हिन्दी</button>
              <button type="button" class="uwa-cat-lang-btn" data-lang="ta" style="padding:2px 7px; border-radius:5px; border:1px solid #cbd5e1; background:#fff; color:#334155; font-size:10.5px; font-weight:600; cursor:pointer;">தமிழ்</button>
            </div>
          </div>
          <div id="uwaDigitalCatDesc" style="font-size:10.5px; color:#15803d; line-height:1.4; margin-bottom:8px;">
            Sends personalized Har Ghar Solar Digital Catalog link with 90% savings, ₹78,000 subsidy &amp; ₹1 scheme details.
          </div>
          <button type="button" id="uwaInsertDigitalCatBtn" style="width:100%; padding:6px 10px; background:#15803d; color:#fff; border:none; border-radius:7px; font-size:11.5px; font-weight:700; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:6px;">
            <i class="fas fa-link"></i> <span id="uwaDigitalCatBtnLabel">Insert Personalized Solar Catalog Link</span>
          </button>
        </div>

        <!-- Official Meta / Database Templates -->
        <div class="uwa-section-label">📑 Select Official Template</div>
        <div style="display:flex; gap:6px; margin-bottom:8px;">
          <select id="uwaCanonicalSeg" style="flex:1; font-size:11.5px; padding:6px; border:1px solid #cbd5e1; border-radius:8px; background:#fff;">
            <option value="">🏢 All Segments</option>
            <option value="solar">☀️ Solar</option>
            <option value="general">💬 General</option>
            <option value="myntreal_real">🏡 Real Estate</option>
            <option value="ev_b2c">⚡ EV B2C</option>
            <option value="ev_b2b">⚡ EV B2B</option>
            <option value="EV_SPARES">🔧 EV Spares</option>
            <option value="etc_training">🎓 ETC Training</option>
            <option value="partner">🤝 Channel Partner</option>
            <option value="leads">🎯 CRM Leads</option>
            <option value="staff">👔 Internal Staff</option>
            <option value="vgk">💼 VGK Executive</option>
            <option value="system">⚙️ System</option>
          </select>
          <select id="uwaCanonicalCat" style="flex:1; font-size:11.5px; padding:6px; border:1px solid #cbd5e1; border-radius:8px; background:#fff;">
            <option value="">All Categories</option>
            <option value="MARKETING">Marketing</option>
            <option value="UTILITY">Utility</option>
            <option value="AUTHENTICATION">Authentication</option>
          </select>
        </div>

        <!-- Template Search and Add Row -->
        <div style="display:flex; gap:6px; margin-bottom:8px;">
          <div style="position:relative; flex:1;">
            <input type="text" id="uwaCanonicalSearch" placeholder="🔍 Search template content or name..." style="width:100%; font-size:11.5px; border:1px solid #cbd5e1; border-radius:8px; padding:6px 10px; background:#fff; outline:none;" />
          </div>
          <button type="button" id="uwaToggleAddTplBtn" style="padding:5px 9px; font-size:11px; font-weight:700; background:#f0fdf4; color:#15803d; border:1px solid #86efac; border-radius:8px; cursor:pointer; white-space:nowrap;">
            <i class="fas fa-plus"></i> Add
          </button>
        </div>

        <!-- Inline Add New Template Card (collapsible) -->
        <div id="uwaAddTplCard" style="display:none; background:#f8fafc; border:1.5px dashed #16a34a; border-radius:10px; padding:10px; margin-bottom:10px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <strong style="font-size:12px; color:#15803d;"><i class="fas fa-plus-circle me-1"></i>New Approved Template</strong>
            <button type="button" id="uwaCancelAddTplBtn" style="background:none; border:none; color:#64748b; font-size:16px; cursor:pointer;">&times;</button>
          </div>
          <div style="display:flex; gap:6px; margin-bottom:6px;">
            <input type="text" id="uwaNewTplName" placeholder="Template Name *" style="flex:2; font-size:11.5px; border:1px solid #cbd5e1; border-radius:6px; padding:5px 8px;" />
            <select id="uwaNewTplSeg" style="flex:1; font-size:11px; border:1px solid #cbd5e1; border-radius:6px; padding:5px 6px; background:#fff;">
              <option value="solar">☀️ Solar</option>
              <option value="general">💬 General</option>
              <option value="myntreal_real">🏡 Real Estate</option>
              <option value="ev_b2c">⚡ EV B2C</option>
              <option value="ev_b2b">⚡ EV B2B</option>
              <option value="EV_SPARES">🔧 EV Spares</option>
              <option value="etc_training">🎓 ETC Training</option>
              <option value="partner">🤝 Partner</option>
              <option value="leads">🎯 Leads</option>
              <option value="staff">👔 Staff</option>
              <option value="vgk">💼 VGK</option>
              <option value="system">⚙️ System</option>
            </select>
          </div>
          <textarea id="uwaNewTplBody" rows="3" placeholder="Template message content with {{1}} customer name, {{2}} details..." style="width:100%; font-size:11.5px; border:1px solid #cbd5e1; border-radius:6px; padding:6px 8px; margin-bottom:6px;"></textarea>
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <small style="font-size:10px; color:#15803d;"><i class="fas fa-check"></i> Auto-approved for API</small>
            <button type="button" id="uwaSaveNewTplBtn" style="padding:4px 10px; font-size:11.5px; font-weight:700; background:#16a34a; color:#fff; border:none; border-radius:6px; cursor:pointer;">
              Save &amp; Use
            </button>
          </div>
        </div>

        <div style="margin-bottom:10px;">
          <select id="uwaCanonicalTpl" style="width:100%; font-size:12px; border:1px solid #cbd5e1; border-radius:8px; padding:7px 10px; background:#fff;">
            <option value="">— Loading templates… —</option>
          </select>
          <div id="uwaNoTplNotice" style="display:none; font-size:11px; color:#b45309; background:#fef3c7; border:1px solid #fde68a; border-radius:6px; padding:6px 8px; margin-top:4px;">
            No approved templates found for this filter.
          </div>
        </div>

        <!-- Dynamic Variable Inputs -->
        <div id="uwaCanonicalVarsWrap" style="display:none; margin-bottom:10px; background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:8px 10px;">
          <div style="font-size:10px; font-weight:700; color:#64748b; text-transform:uppercase; margin-bottom:6px;">Fill Variables</div>
          <div id="uwaCanonicalVarsBox"></div>
        </div>

        <!-- Quick Template Chips -->
        <div class="uwa-section-label">Contextual Quick Chips</div>
        <div class="uwa-chips-row">
          ${Object.entries(QUICK_TEMPLATES).map(([key, tpl]) => `
            <button class="uwa-chip-btn" data-tpl-key="${key}">
              ${tpl.label}
            </button>
          `).join('')}
        </div>

        <!-- Message Composer -->
        <div class="uwa-section-label mt-2">
          Message
          <small class="text-muted" style="float:right; font-weight:normal; text-transform:none;">
            ✍️ Auto-signed with your staff identity
          </small>
        </div>
        <textarea id="uwaMessageText" class="uwa-textarea" rows="7" placeholder="Type your WhatsApp message...">${this.escapeHtml(initialText)}</textarea>

        <!-- Status & Result feedback -->
        <div id="uwaFeedbackBox" class="uwa-feedback-box" style="display:none;"></div>

        <!-- Action Footer -->
        <div class="uwa-footer">
          <button class="btn btn-outline uwa-cancel-btn" id="uwaCancelBtn">Cancel</button>
          <button class="btn btn-primary uwa-send-btn" id="uwaSendBtn">
            <i class="fas fa-paper-plane me-1"></i>
            <span id="uwaSendBtnLabel">Send via 📱 Scanned WhatsApp</span>
          </button>
        </div>
      </div>
    `;

    document.body.appendChild(this.modalEl);

    const detected = this.detectSegment();
    const segEl = document.getElementById('uwaCanonicalSeg') as HTMLSelectElement;
    if (segEl && detected) {
      segEl.value = detected;
    }

    const detectedCatKey = this.detectCatalogKey();
    const catSel = document.getElementById('uwaDigitalCatSel') as HTMLSelectElement;
    if (catSel && detectedCatKey) {
      catSel.value = detectedCatKey;
    }
    this.onDigitalCatalogSelect(detectedCatKey);

    this.attachEvents();
    void this.loadCanonicalTemplates();
  }

  private attachEvents(): void {
    if (!this.modalEl) return;

    document.getElementById('uwaCloseBtn')?.addEventListener('click', () => this.close());
    document.getElementById('uwaCancelBtn')?.addEventListener('click', () => this.close());

    // 1-Tap Quick Responses
    document.getElementById('uwaQuickThanksBtn')?.addEventListener('click', () => this.applyVerticalQuick('thanks_connecting'));
    document.getElementById('uwaQuickReachBtn')?.addEventListener('click', () => this.applyVerticalQuick('trying_to_reach'));

    // Digital Catalog Events
    document.getElementById('uwaDigitalCatSel')?.addEventListener('change', (e) => {
      this.onDigitalCatalogSelect((e.target as HTMLSelectElement).value);
    });
    this.modalEl.querySelectorAll('.uwa-cat-lang-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const lang = (e.currentTarget as HTMLElement).getAttribute('data-lang') || 'te';
        this.applyDigitalCatalog(lang);
      });
    });
    document.getElementById('uwaInsertDigitalCatBtn')?.addEventListener('click', () => {
      this.applyDigitalCatalog();
    });

    // Canonical Template Engine Events
    document.getElementById('uwaCanonicalSeg')?.addEventListener('change', () => this.filterCanonicalTemplates());
    document.getElementById('uwaCanonicalCat')?.addEventListener('change', () => this.filterCanonicalTemplates());
    document.getElementById('uwaCanonicalSearch')?.addEventListener('input', () => this.filterCanonicalTemplates());
    document.getElementById('uwaCanonicalTpl')?.addEventListener('change', () => this.onCanonicalTplChange());
    document.getElementById('uwaToggleAddTplBtn')?.addEventListener('click', () => this.toggleAddTemplateCard());
    document.getElementById('uwaCancelAddTplBtn')?.addEventListener('click', () => this.toggleAddTemplateCard(false));
    document.getElementById('uwaSaveNewTplBtn')?.addEventListener('click', () => this.saveNewTemplate());

    // Mode Toggle
    document.getElementById('uwaModeScannedBtn')?.addEventListener('click', () => {
      this.activeMode = 'scanned';
      this.updateModeUI();
      void this.loadCanonicalTemplates();
    });

    document.getElementById('uwaModeMetaBtn')?.addEventListener('click', () => {
      this.activeMode = 'meta_api';
      this.updateModeUI();
      void this.loadCanonicalTemplates();
    });

    // Template Chips
    this.modalEl.querySelectorAll('.uwa-chip-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const key = (e.currentTarget as HTMLElement).dataset.tplKey;
        if (key && QUICK_TEMPLATES[key]) {
          const signature = this.getSenderSignature();
          const textEl = document.getElementById('uwaMessageText') as HTMLTextAreaElement;
          if (textEl) {
            textEl.value = QUICK_TEMPLATES[key].text + signature;
            textEl.focus();
          }
        }
      });
    });

    // Send Button
    document.getElementById('uwaSendBtn')?.addEventListener('click', () => this.handleSend());
  }

  private updateModeUI(): void {
    const scannedBtn = document.getElementById('uwaModeScannedBtn');
    const metaBtn = document.getElementById('uwaModeMetaBtn');
    const sendBtnLabel = document.getElementById('uwaSendBtnLabel');
    const sendBtn = document.getElementById('uwaSendBtn') as HTMLButtonElement;

    if (this.activeMode === 'scanned') {
      scannedBtn?.classList.add('active');
      metaBtn?.classList.remove('active');
      if (sendBtnLabel) sendBtnLabel.textContent = 'Send via 📱 Scanned WhatsApp';
      if (sendBtn) sendBtn.style.background = '#16a34a';
    } else {
      scannedBtn?.classList.remove('active');
      metaBtn?.classList.add('active');
      if (sendBtnLabel) sendBtnLabel.textContent = 'Send via 🏢 Official WhatsApp';
      if (sendBtn) sendBtn.style.background = '#2563eb';
    }
  }

  private async handleSend(): Promise<void> {
    if (!this.currentOptions) return;

    const textEl = document.getElementById('uwaMessageText') as HTMLTextAreaElement;
    const sendBtn = document.getElementById('uwaSendBtn') as HTMLButtonElement;
    const sendBtnLabel = document.getElementById('uwaSendBtnLabel');

    let msg = (textEl?.value || '').trim();
    if (!msg) {
      this.showFeedback('Please enter a message to send.', 'error');
      return;
    }

    // Ensure sender signature is attached without duplicates
    const sig = this.getSenderSignature();
    if (!msg.toLowerCase().includes('regards,')) {
      msg = msg + sig;
    }

    const { phone, name, leadId } = this.currentOptions;
    const cleanPhone = (phone || '').replace(/\D/g, '').slice(-10);
    const hasValidLeadId = !!(leadId && leadId !== 'new' && !isNaN(Number(leadId)));

    if ((!cleanPhone || cleanPhone.length < 10) && !hasValidLeadId) {
      this.showFeedback('Invalid recipient phone number.', 'error');
      return;
    }

    if (sendBtn) sendBtn.disabled = true;

    // Mode 1: WhatsApp API (Meta Cloud)
    if (this.activeMode === 'meta_api') {
      if (sendBtnLabel) sendBtnLabel.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Sending via Meta API...';
      this.showFeedback('Dispatching via WhatsApp Cloud API...', 'info');

      try {
        const leadTargetId = hasValidLeadId ? Number(leadId) : 0;
        const response = await apiService.post<any>(`/whatsapp-config/crm-lead-send/${leadTargetId}`, {
          phone: cleanPhone.length >= 10 ? cleanPhone : undefined,
          custom_message: msg,
          send_mode: 'company'
        });

        if (response.success) {
          if (sendBtnLabel) sendBtnLabel.innerHTML = '<i class="fas fa-check me-1"></i> Sent Successfully ✓';
          this.showFeedback('✅ Dispatched via WhatsApp Meta Cloud API (Official Business)', 'success');
          setTimeout(() => this.close(), 2500);
        } else {
          const errorMsg = response.error || response.data?.reason || 'Meta API not available.';
          this.showFeedback(`❌ Meta API Error: ${errorMsg}`, 'error');
          if (sendBtn) sendBtn.disabled = false;
          if (sendBtnLabel) sendBtnLabel.textContent = 'Retry Send';
        }
      } catch (err: any) {
        console.warn('[UnifiedWAModal] Meta API failed:', err);
        this.showFeedback(`❌ Meta API Network error: ${err.message || 'Server unreachable'}`, 'error');
        if (sendBtn) sendBtn.disabled = false;
        if (sendBtnLabel) sendBtnLabel.textContent = 'Retry Send';
      }
      return;
    }

    // Mode 2: Scan WhatsApp (Personal / Common Number)
    if (sendBtnLabel) sendBtnLabel.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Sending via Personal WA...';
    this.showFeedback('Connecting to WhatsApp Bot Gateway...', 'info');

    try {
      const response = await apiService.post<any>('/whatsapp/send-message', {
        recipient: cleanPhone.length >= 10 ? cleanPhone : 'LEAD_RESOLVE',
        message: msg,
        recipient_type: 'individual',
        recipient_name: name || 'Customer',
        lead_id: hasValidLeadId ? Number(leadId) : (leadId || null)
      });

      if (response.success) {
        if (sendBtnLabel) sendBtnLabel.innerHTML = '<i class="fas fa-check me-1"></i> Sent Successfully ✓';
        this.showFeedback(`✅ Dispatched via Personal Scanned WhatsApp! Sender: ${this.escapeHtml(authService.getAuthState().user?.full_name || 'Staff')}`, 'success');
        setTimeout(() => this.close(), 2500);
      } else {
        const errorMsg = response.error || 'Personal WhatsApp Web is disconnected or unlinked.';
        this.showFeedback(`❌ Personal WA: ${errorMsg}. You can switch to "WhatsApp API" mode above to send via Official Meta Business.`, 'error');
        if (sendBtn) sendBtn.disabled = false;
        if (sendBtnLabel) sendBtnLabel.textContent = 'Retry Send';
      }
    } catch (err: any) {
      console.error('[UnifiedWAModal] Send error:', err);
      this.showFeedback(`❌ Personal WhatsApp Gateway offline. You can switch to "WhatsApp API" above to send via Meta Cloud.`, 'error');
      if (sendBtn) sendBtn.disabled = false;
      if (sendBtnLabel) sendBtnLabel.textContent = 'Retry Send';
    }
  }

  private showFeedback(msg: string, type: 'info' | 'success' | 'error'): void {
    const feedbackBox = document.getElementById('uwaFeedbackBox');
    if (!feedbackBox) return;
    feedbackBox.style.display = 'block';
    feedbackBox.className = `uwa-feedback-box ${type}`;
    feedbackBox.innerHTML = msg;
  }

  private maskPhone(p: string): string {
    if (!p) return '-';
    const digits = String(p).replace(/\D/g, '');
    if (digits.length >= 10) {
      return '+91 ' + digits.slice(-10, -8) + '••••' + digits.slice(-4);
    }
    if (digits.length >= 4) {
      return '••••' + digits.slice(-4);
    }
    return '••••';
  }

  private escapeHtml(text: string): string {
    const map: Record<string, string> = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;'
    };
    return (text || '').replace(/[&<>"']/g, m => map[m]);
  }
}

export const unifiedWAModal = new UnifiedWAModal();
