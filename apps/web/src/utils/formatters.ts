import { getCongestionColor, getCongestionLabel } from './constants';
export { getCongestionColor, getCongestionLabel };

export function formatSpeed(mps: number | null | undefined, unit: 'kmph' | 'mps' = 'kmph'): string {
  if (mps === null || mps === undefined) return 'N/A';
  if (unit === 'kmph') {
    const kmph = Math.round(mps * 3.6 * 10) / 10;
    return `${kmph} km/h`;
  }
  return `${Math.round(mps * 10) / 10} m/s`;
}

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || !Number.isFinite(seconds)) {
    return 'Unreachable';
  }
  if (seconds === 0) return '0s';
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  if (mins === 0) return `${secs}s`;
  if (secs === 0) return `${mins}m`;
  return `${mins}m ${secs}s`;
}

export function formatDistance(meters: number | null | undefined): string {
  if (meters === null || meters === undefined || !Number.isFinite(meters)) {
    return '0 m';
  }
  if (meters >= 1000) {
    return `${(meters / 1000).toFixed(2)} km`;
  }
  return `${Math.round(meters)} m`;
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
      timeZone: 'UTC',
    }) + ' UTC';
  } catch {
    return iso;
  }
}

export function formatTimeOnly(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
      timeZone: 'UTC',
    }) + ' UTC';
  } catch {
    return iso;
  }
}

export function getOutcomeBadgeProps(outcome: string | undefined): {
  label: string;
  variant: 'emerald' | 'amber' | 'red' | 'slate';
  description: string;
} {
  switch (outcome) {
    case 'ROBUST_ALTERNATIVE':
      return {
        label: 'Robust Alternative Route',
        variant: 'emerald',
        description: 'Alternative route is faster across all tested scenarios (both slowdown and full closure).',
      };
    case 'EVIDENCE_SENSITIVE':
      return {
        label: 'Evidence-Sensitive Recommendation',
        variant: 'amber',
        description: 'Preferred route flips between slowdown and closure; verifying incident blockage is critical.',
      };
    case 'NO_ROUTE_AVAILABLE':
      return {
        label: 'No Alternative Route Available',
        variant: 'red',
        description: 'Corridor closure leaves destination unreachable via network.',
      };
    case 'INSUFFICIENT_DATA':
    default:
      return {
        label: 'Insufficient Data / Disconnected',
        variant: 'slate',
        description: 'Available network connectivity is insufficient for reliable routing comparison.',
      };
  }
}
