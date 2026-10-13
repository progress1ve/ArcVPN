// @vitest-environment jsdom
import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import ArcNodePreflight from './ArcNodePreflight';
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
it('requires independent trust, clears credentials after errors and invalidates changed targets',async()=>{
  const request=vi.fn().mockResolvedValue({ok:false,json:async()=>({error:'ssh_auth_failed'})});
  vi.stubGlobal('fetch',request);
  render(<ArcNodePreflight initialOpen/>);
  fireEvent.change(screen.getByLabelText('Публичный IP'),{target:{value:'203.0.113.10'}});
  fireEvent.change(screen.getByLabelText('Подтверждённый SSH fingerprint'),{target:{value:'SHA256:'+'A'.repeat(43)}});
  const password=screen.getByLabelText('SSH пароль') as HTMLInputElement;
  fireEvent.change(password,{target:{value:'test-only-placeholder'}});
  const submit=screen.getByRole('button',{name:'Проверить доступ и сервер'}) as HTMLButtonElement;
  expect(submit.disabled).toBe(true);
  const trust=screen.getByRole('checkbox') as HTMLInputElement;
  fireEvent.click(trust);
  expect(submit.disabled).toBe(false);
  fireEvent.click(submit);
  expect(await screen.findByRole('alert')).toBeTruthy();
  await waitFor(()=>expect(password.value).toBe(''));
  expect(screen.getByRole('alert').textContent).toContain('Сервер не принял логин или пароль');
  fireEvent.change(screen.getByLabelText('SSH порт'),{target:{value:'2222'}});
  expect((screen.getByLabelText('Подтверждённый SSH fingerprint') as HTMLInputElement).value).toBe('');
  expect(trust.checked).toBe(false);
  expect(screen.queryByText('Предварительный состав полного preset')).toBeNull();
});
