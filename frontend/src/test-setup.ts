import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'

// Each test mounts its own tree; nothing is left in the document for the next one.
afterEach(cleanup)
