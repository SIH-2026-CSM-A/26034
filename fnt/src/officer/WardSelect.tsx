import { useMemo } from 'react';
import { GHMC_WARDS, GHMC_ZONES } from './dashboard/ghmcWards';

interface Props {
  value: string;
  onChange: (wardName: string) => void;
  id?: string;
  className?: string;
}

/**
 * The GHMC ward the officer is inspecting in, chosen at submission. A native `<select>`
 * grouped by zone — no dependency, works the same on a phone as on the desk, and its
 * option values are the exact ward labels the dashboard map shades, so a submission and
 * its polygon can never drift apart. Optional: the empty value records no ward.
 */
export function WardSelect({ value, onChange, id, className }: Props) {
  const byZone = useMemo(() => {
    const groups = new Map<string, typeof GHMC_WARDS[number][]>();
    for (const zone of GHMC_ZONES) groups.set(zone, []);
    for (const ward of GHMC_WARDS) {
      const list = groups.get(ward.zone);
      if (list) list.push(ward);
    }
    return groups;
  }, []);

  return (
    <select
      id={id}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={className}
    >
      <option value="">No ward recorded</option>
      {GHMC_ZONES.map((zone) => (
        <optgroup key={zone} label={`${zone} Zone`}>
          {(byZone.get(zone) ?? []).map((ward) => (
            <option key={ward.num} value={ward.name}>
              {ward.name}
            </option>
          ))}
        </optgroup>
      ))}
    </select>
  );
}
