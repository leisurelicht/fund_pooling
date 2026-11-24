// Google Identity Services (GIS) — 类型声明
// https://developers.google.com/identity/gsi/web/reference/js-reference
// 官方无 npm 类型包，SDK 由 https://accounts.google.com/gsi/client 注入全局

interface GoogleCredentialResponse {
  /** 后端用来校验的 ID token（JWT） */
  credential: string
  select_by?: string
  clientId?: string
}

interface GoogleIdConfiguration {
  client_id: string
  callback: (response: GoogleCredentialResponse) => void
  auto_select?: boolean
  cancel_on_tap_outside?: boolean
  ux_mode?: 'popup' | 'redirect'
  context?: 'signin' | 'signup' | 'use'
  login_uri?: string
  nonce?: string
  use_fedcm_for_prompt?: boolean
}

interface GoogleButtonOptions {
  type?: 'standard' | 'icon'
  theme?: 'outline' | 'filled_blue' | 'filled_black'
  size?: 'large' | 'medium' | 'small'
  text?: 'signin_with' | 'signup_with' | 'continue_with' | 'signin'
  shape?: 'rectangular' | 'pill' | 'circle' | 'square'
  logo_alignment?: 'left' | 'center'
  width?: number | string
  locale?: string
}

interface GoogleAccountsId {
  initialize(config: GoogleIdConfiguration): void
  renderButton(parent: HTMLElement, options?: GoogleButtonOptions): void
  disableAutoSelect(): void
  cancel(): void
}

interface Window {
  /** SDK 尚未加载时为 undefined */
  google?: {
    accounts: {
      id: GoogleAccountsId
    }
  }
}
