import { useEffect, useState } from 'react';

/**
 * Trail `value` by `delay` milliseconds.
 *
 * Used for the business search: the input itself stays controlled by the live
 * value so typing feels immediate, while the work the term drives - filtering
 * ~207 records twice over, recounting every filter chip and rebuilding the
 * marker layer - runs once the typing pauses instead of on every keystroke.
 */
export function useDebouncedValue(value, delay = 200) {
  const [settled, setSettled] = useState(value);

  useEffect(() => {
    if (value === settled) return undefined;
    const timer = setTimeout(() => setSettled(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay, settled]);

  return settled;
}
