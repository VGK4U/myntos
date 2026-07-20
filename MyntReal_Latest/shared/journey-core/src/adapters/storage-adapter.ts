import { JourneySession } from '../types/journey.js';

export interface StorageAdapter {
  saveSession(session: JourneySession): Promise<void>;
  
  loadSession(): Promise<JourneySession | null>;
  
  clearSession(): Promise<void>;
  
  hasSession(): Promise<boolean>;
}
