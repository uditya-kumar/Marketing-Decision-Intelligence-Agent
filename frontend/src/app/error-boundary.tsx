import { Component, type ErrorInfo, type ReactNode } from 'react'
import { ErrorState } from '@/components/common/error-state'

type Props = { children: ReactNode }
type State = { failed: boolean }

/** The last line of defence: a crash while rendering shows a message, not a blank page.
 *
 * Keyed by route in the layout, so moving to another screen clears it.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { failed: false }

  static getDerivedStateFromError(): State {
    return { failed: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // Nothing to report this to yet; the console is where a demo would look.
    console.error('screen.crashed', error, info.componentStack)
  }

  render(): ReactNode {
    if (!this.state.failed) return this.props.children
    return (
      <ErrorState
        message="This screen ran into a problem."
        onRetry={() => this.setState({ failed: false })}
      />
    )
  }
}
