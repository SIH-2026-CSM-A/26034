/** A published demo login: shown on the sign-in page so anyone can try the surface. */
export interface DemoAccount {
  role: string
  username: string
  password: string
}

/**
 * The "Demo access" panel. These accounts are deliberately public and see only seeded
 * demonstration data; the README lists the same credentials.
 */
export function DemoAccess({
  accounts,
  disabled,
  onSignIn,
}: {
  accounts: DemoAccount[]
  disabled: boolean
  onSignIn: (account: DemoAccount) => void
}) {
  return (
    <section aria-labelledby="demo-access" className="card mt-4 p-5 sm:p-7">
      <h2 id="demo-access" className="text-body font-semibold">
        Demo access
      </h2>
      <p className="mt-1 text-secondary text-mute">
        Public demonstration accounts. They see seeded demo data only.
      </p>
      <ul className="mt-4 space-y-4">
        {accounts.map((account) => (
          <li key={account.username}>
            <p className="text-secondary font-medium">{account.role}</p>
            <dl className="mt-1 grid grid-cols-[auto_1fr] gap-x-3 text-secondary">
              <dt className="text-mute">Username</dt>
              <dd className="font-mono break-all">{account.username}</dd>
              <dt className="text-mute">Password</dt>
              <dd className="font-mono break-all">{account.password}</dd>
            </dl>
            <button
              type="button"
              disabled={disabled}
              onClick={() => onSignIn(account)}
              className="btn btn-ghost mt-3 w-full text-body"
            >
              Sign in as this user
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}
