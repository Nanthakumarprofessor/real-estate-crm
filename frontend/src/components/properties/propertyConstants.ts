/**
 * Display constants for property-related UI.
 */
import type { UnitStatus, UnitType } from '../../api/propertiesApi';

export const UNIT_TYPE_LABEL: Record<UnitType, string> = {
  '1BHK': '1 BHK',
  '2BHK': '2 BHK',
  '3BHK': '3 BHK',
  '4BHK': '4 BHK',
  'VILLA': 'Villa',
  'PLOT':  'Plot',
};

export const UNIT_TYPE_OPTIONS: { value: UnitType; label: string }[] = [
  { value: '1BHK',  label: '1 BHK'  },
  { value: '2BHK',  label: '2 BHK'  },
  { value: '3BHK',  label: '3 BHK'  },
  { value: '4BHK',  label: '4 BHK'  },
  { value: 'VILLA', label: 'Villa'   },
  { value: 'PLOT',  label: 'Plot'    },
];

export const UNIT_STATUS_LABEL: Record<UnitStatus, string> = {
  AVAILABLE: 'Available',
  BOOKED:    'Booked',
};

export const UNIT_STATUS_BADGE: Record<UnitStatus, string> = {
  AVAILABLE: 'bg-success',
  BOOKED:    'bg-warning text-dark',
};
