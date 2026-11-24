// Apple Sign In JS SDK — 类型声明
// https://developer.apple.com/documentation/sign_in_with_apple/sign_in_with_apple_js

interface AppleIDAuth {
  init(config: {
    clientId: string
    scope: string
    redirectURI?: string
    state?: string
    usePopup?: boolean
  }): void
  signIn(): Promise<AppleSignInResponse>
  renderButton(
    selector: string,
    options?: {
      type?: 'sign-in' | 'continue'
      style?: 'black' | 'white' | 'white-outline'
      borderRadius?: number
      mode?: 'center-align' | 'left-align'
    },
  ): void
}

interface AppleSignInResponse {
  detail: {
    authorization: {
      id_token: string
      code: string
      state: string
    }
    user?: {
      name?: {
        firstName?: string
        lastName?: string
      }
      email?: string
    }
  }
}

interface Window {
  AppleID: {
    auth: AppleIDAuth
  }
}