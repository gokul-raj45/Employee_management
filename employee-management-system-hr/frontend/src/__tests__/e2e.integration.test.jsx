// REAL end-to-end test: React UI -> axios -> live Flask API -> PostgreSQL. No mocked API.
// Opt-in: set E2E_API_URL (+ VITE_API_BASE_URL to the same value), E2E_ADMIN_EMAIL, E2E_ADMIN_PASSWORD.
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import App from '../App'
import { AuthProvider } from '../auth/AuthContext'
import { ToastProvider } from '../components/ui'

const E2E = import.meta.env.VITE_E2E === 'true'
const ADMIN = { email: import.meta.env.VITE_E2E_ADMIN_EMAIL, password: import.meta.env.VITE_E2E_ADMIN_PASSWORD }
const suffix = Math.random().toString(36).slice(2, 8)
const EMP = { name: `Test Person ${suffix}`, email: `tp-${suffix}@example.com`, temp: 'TempPass#12345', next: 'BrandNew#12345' }

const mount = (path = '/') => render(
  <MemoryRouter initialEntries={[path]}><AuthProvider><ToastProvider><App /></ToastProvider></AuthProvider></MemoryRouter>)
const nav = async (user, name) => user.click(await screen.findByRole('link', { name }))

async function signIn(user, email, password) {
  await user.type(await screen.findByLabelText(/^email/i), email)
  await user.type(screen.getByLabelText(/^password/i), password)
  await user.click(screen.getByRole('button', { name: /sign in/i }))
}

describe.skipIf(!E2E)('full workflow against the live backend', () => {
  beforeEach(() => sessionStorage.clear())

  it('rejects a wrong password with the server message and stays on login', async () => {
    const user = userEvent.setup(); mount()
    await signIn(user, ADMIN.email, 'definitely-wrong')
    expect(await screen.findByRole('alert')).toHaveTextContent(/invalid email or password/i)
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('admin creates employee + salary; employee changes password, requests leave; admin approves; employee sees payslip', async () => {
    const user = userEvent.setup()

    // ---- admin signs in, dashboard shows real stats
    let view = mount(); await signIn(user, ADMIN.email, ADMIN.password)
    expect(await screen.findByRole('heading', { name: /hello, admin/i })).toBeInTheDocument()
    expect(await screen.findByText(/total employees/i)).toBeInTheDocument()

    // ---- admin creates an employee with a login
    await nav(user, /employee details/i)
    await user.click(await screen.findByRole('button', { name: /add employee/i }))
    await user.type(screen.getByLabelText(/full name/i), EMP.name)
    await user.type(screen.getByLabelText(/work email/i), EMP.email)
    await user.type(screen.getByLabelText(/^department \*/i), 'Engineering')
    await user.type(screen.getByLabelText(/^designation/i), 'QA Engineer')
    await user.type(screen.getByLabelText(/initial password/i), EMP.temp)
    await user.click(screen.getByRole('button', { name: /save employee/i }))
    expect(await screen.findByText(EMP.email)).toBeInTheDocument()

    // ---- search filters the table through the API
    await user.type(screen.getByLabelText('Search'), `zzz-no-match-${suffix}`)
    expect(await screen.findByText(/no employee records found/i)).toBeInTheDocument()

    // ---- admin adds a salary record; net salary is computed by the server
    await nav(user, /salary details/i)
    await user.click(await screen.findByRole('button', { name: /add salary record/i }))
    const select = await screen.findByLabelText(/^employee/i)
    await waitFor(() => expect(within(select).getByText(new RegExp(EMP.name))).toBeInTheDocument())
    await user.selectOptions(select, within(select).getByText(new RegExp(EMP.name)))
    await user.type(screen.getByLabelText(/basic salary/i), '50000')
    await user.clear(screen.getByLabelText(/allowances/i)); await user.type(screen.getByLabelText(/allowances/i), '5000')
    await user.clear(screen.getByLabelText(/deductions/i)); await user.type(screen.getByLabelText(/deductions/i), '2500')
    await user.click(screen.getByRole('button', { name: /save salary/i }))
    const row = await screen.findByRole('row', { name: new RegExp(EMP.name) })   // scope to THIS run's employee
    expect(within(row).getByText(/52,500\.00/)).toBeInTheDocument()            // 50000 + 5000 - 2500, computed by the server
    view.unmount(); sessionStorage.clear()

    // ---- employee: first login forces password change
    view = mount(); await signIn(user, EMP.email, EMP.temp)
    expect(await screen.findByText(/must change your temporary password/i)).toBeInTheDocument()
    await user.type(screen.getByLabelText(/^current password/i), EMP.temp)
    await user.type(screen.getByLabelText(/^new password/i), EMP.next)
    await user.type(screen.getByLabelText(/^confirm new password/i), EMP.next)
    await user.click(screen.getByRole('button', { name: /change password/i }))
    await waitFor(() => expect(screen.queryByText(/must change your temporary password/i)).toBeNull())

    // ---- employee sees only own data and no admin navigation
    expect(screen.queryByRole('link', { name: /reports/i })).toBeNull()
    await nav(user, /employee details/i)
    expect(await screen.findByText(EMP.email)).toBeInTheDocument()

    // ---- employee views own payslip
    await nav(user, /salary details/i)
    await user.click(await screen.findByRole('button', { name: /view payslip/i }))
    const slip = await screen.findByRole('dialog', { name: /payslip/i })
    expect(await within(slip).findByText(/gross earnings/i)).toBeInTheDocument()
    expect(within(slip).getAllByText(/52,500\.00/).length).toBeGreaterThan(0)
    await user.click(within(slip).getAllByRole('button', { name: /close/i }).at(-1))

    // ---- employee requests leave
    await nav(user, /leave requests/i)
    await user.click(await screen.findByRole('button', { name: /request leave/i }))
    await user.type(screen.getByLabelText(/reason/i), 'Family function')
    await user.click(screen.getByRole('button', { name: /submit request/i }))
    expect(await screen.findByText('Pending')).toBeInTheDocument()
    view.unmount(); sessionStorage.clear()

    // ---- admin approves
    view = mount(); await signIn(user, ADMIN.email, ADMIN.password)
    await nav(user, /leave requests/i)
    const leaveRow = await screen.findByRole('row', { name: new RegExp(EMP.name) })
    await user.click(within(leaveRow).getByRole('button', { name: /approve/i }))
    const dlg = await screen.findByRole('dialog', { name: /approve leave/i })
    await user.click(within(dlg).getByRole('button', { name: /^approve$/i }))
    await waitFor(() => expect(within(screen.getByRole('row', { name: new RegExp(EMP.name) })).getByText('Approved')).toBeInTheDocument())

    // ---- the action is in the audit trail
    await nav(user, /reports & activity/i)
    expect((await screen.findAllByText('leave.approved')).length).toBeGreaterThan(0)
    view.unmount(); sessionStorage.clear()

    // ---- employee sees the approved status
    view = mount(); await signIn(user, EMP.email, EMP.next)
    await nav(user, /leave requests/i)
    expect(await screen.findByText('Approved')).toBeInTheDocument()
  })

  it('an employee who opens an admin-only URL is sent back to the dashboard', async () => {
    const user = userEvent.setup()
    mount('/reports')                                   // anonymous -> redirected to /login, remembering /reports
    await signIn(user, EMP.email, EMP.next)             // employee created by the previous test
    expect(await screen.findByRole('heading', { name: /^hello/i })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: /reports & activity/i })).toBeNull()
  })
})
