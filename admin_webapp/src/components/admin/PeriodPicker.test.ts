import {describe,it,expect} from 'vitest';
import {periodDates} from './PeriodPicker';
describe('Moscow calendar presets',()=>{
 it('switches month at Moscow midnight and keeps inclusive days',()=>{
  const now=new Date('2026-09-30T21:01:00Z');
  expect(periodDates('month',now)).toEqual({from:'2026-10-01',to:'2026-10-01'});
  expect(periodDates('week',now)).toEqual({from:'2026-09-25',to:'2026-10-01'});
  expect(periodDates('30days',now)).toEqual({from:'2026-09-02',to:'2026-10-01'});
  expect(periodDates('all',now)).toEqual({from:'',to:''});
 });
});
