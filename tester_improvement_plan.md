# Tester Improvement Plan

## Objective
To improve the observability of the integration tester by enabling real-time dual-channel output (Console + Timestamped Log File) and ensuring comprehensive state inspection after each turn.

## Analysis of Current Implementation
- **File**: `src/tester/runner.py`
- **Current Behavior**:
  - Uses `print()` for narratives and state snapshots (goes to stdout).
  - Uses `logger` for system events (setup, errors).
  - Collects results in a list and prints the full JSON report only at the end.
  - Already queries `get_session_state` (which fetches Session, Player, NPCs, Enemies, Sequence) after each turn.

## Required Changes

### 1. Dual-Channel Logging Setup
- **Action**: Modify `IntegrationTestRunner.__init__` or global setup in `runner.py`.
- **Implementation**:
  - Create a log filename with timestamp: `test_output_{YYYYMMDD_HHMMSS}.log`.
  - Configure the root logger or a specific `gtrpgm.tester` logger to have:
    - `StreamHandler`: Prints to Console.
    - `FileHandler`: Writes to the log file.
  - Set level to `INFO`.

### 2. Output Standardization
- **Action**: Replace `print()` statements with a unified logging method.
- **Implementation**:
  - Convert `_print_state_snapshot` to use `logger.info` (formatting the output nicely).
  - Convert `_print_scenario_manifest` to use `logger.info`.
  - Inside the turn loop, log the Player Action, GM Narrative, and NPC Narrative using `logger.info`.

### 3. Real-time Result Feedback
- **Action**: Ensure turn results are visible immediately.
- **Implementation**:
  - The current loop already prints narratives. By moving to `logger`, these will appear in the file immediately.
  - Add a log entry explicitly stating "Turn X Result: Success" with key metrics if available.

### 4. Verification of State Query
- **Action**: Confirm `client.get_session_state` matches GM's logic.
- **Status**: Checked `src/tester/client.py`. It aggregates data from Session, Player, NPC, Enemy, and Sequence endpoints. This matches the requirement.
- **Task**: Ensure the `_print_state_snapshot` method (renamed to `_log_state_snapshot`) is called and logged effectively after every turn.

## Execution Steps
1.  Modify `src/tester/runner.py` to implement the logging changes.
2.  Run a short test (5 turns) to verify the output creates a file and streams to console.
