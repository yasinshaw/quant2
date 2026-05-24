---
name: url-extractor
description: Extract data from quant2 platform URLs by calling backend APIs. Use when user provides a URL like http://localhost:3002/results/343 and wants to analyze the data. Supports backtest results, optimization results, trade lists, and more. Triggers include URL input, "extract data from URL", "analyze result", "查看结果", "提取数据".
---

# URL Data Extractor

Extract and analyze data from quant2 platform URLs by calling backend APIs.

## Prerequisites

Verify backend is running:
```bash
curl -s http://localhost:8000/api/v1/strategies/ | head -c 200
```

If not running:
```bash
cd /Users/yasin/code/quant2 && ./start.sh start
```

## URL Pattern Recognition

The skill supports these URL patterns:

| URL Pattern | Resource Type | Backend API |
|-------------|---------------|-------------|
| `http://localhost:3002/results/{id}` | Backtest result | `GET /api/v1/backtest/jobs/{id}/report` |
| `http://localhost:3002/optimize` | Optimization history | `GET /api/v1/backtest/optimization/history` |
| `http://localhost:3002/strategies` | Strategy list | `GET /api/v1/strategies/` |
| `http://localhost:3002/data` | Data status | `GET /api/v1/data/status` |
| `http://localhost:3002/live` | Live trading status | `GET /api/v1/live/status` |

## Extraction Workflow

### Step 1: Parse URL

Extract the resource type and ID from the user's URL:

```python
# Example URL: http://localhost:3002/results/343
# Pattern: /results/{job_id}
# Resource type: backtest_result
# ID: 343 (job_id)
```

### Step 2: Call Backend API

Based on the URL pattern, call the appropriate backend API.

**For backtest results (`/results/{id}`):**

```bash
curl -s http://localhost:8000/api/v1/backtest/jobs/{id}/report
```

**For optimization results:**

```bash
# Get optimization job results
curl -s http://localhost:8000/api/v1/backtest/optimization/jobs/{id}/results

# Get stability analysis
curl -s http://localhost:8000/api/v1/backtest/optimization/jobs/{id}/stability
```

### Step 3: Format and Display Data

Extract key metrics and present them in a structured format:

**Backtest Result Key Metrics:**
- Strategy name and parameters
- Time range (start_time, end_time)
- Total return, Sharpe ratio, Max drawdown
- Win rate, Profit factor
- Trade count
- Calmar ratio (if available)

**Optimization Result Key Metrics:**
- Best parameters and score
- All results sorted by score
- Stability score (if available)

### Step 4: Provide Analysis Context

After extracting the data, provide context:

1. **Performance Assessment**: Is the result good, average, or poor?
2. **Key Insights**: What stands out in the data?
3. **Comparison Points**: How does this compare to benchmarks or expectations?
4. **Next Steps**: What should the user consider doing next?

## API Reference

### Backtest Results

**Get full backtest report:**
```
GET /api/v1/backtest/jobs/{job_id}/report
```

Response includes:
- `summary`: Performance metrics
- `monthly_returns`: Monthly breakdown
- `trade_analysis`: Per-trade statistics
- `equity_curve`: Equity data points
- `strategy_name`: Strategy used
- `parameters`: Parameters used
- `dataset`: Dataset information

**Get job status:**
```
GET /api/v1/backtest/jobs/{job_id}
```

**Get trades for job:**
```
GET /api/v1/backtest/results/{result_id}/trades
```

### Optimization Results

**Get optimization results:**
```
GET /api/v1/backtest/optimization/jobs/{job_id}/results
```

**Get stability analysis:**
```
GET /api/v1/backtest/optimization/jobs/{job_id}/stability
```

**Get optimization history:**
```
GET /api/v1/backtest/optimization/history
```

### Live Trading

**Get live trading status:**
```
GET /api/v1/live/status
```

**Get live trades:**
```
GET /api/v1/live/trades
```

### Data Management

**Get available datasets:**
```
GET /api/v1/data/datasets
```

**Get data status for symbol:**
```
GET /api/v1/data/status?symbol=ETHUSDT&interval=4h
```

## Output Format Template

### For Backtest Results:

```markdown
## Backtest Result Analysis

**URL**: {user_url}
**Job ID**: {job_id}

### Strategy
- **Name**: {strategy_name}
- **Parameters**: {formatted_parameters}

### Dataset
- **Symbol**: {symbol}
- **Interval**: {interval}
- **Time Range**: {start_time} to {end_time}

### Performance Metrics
| Metric | Value |
|--------|-------|
| Total Return | {return}% |
| Sharpe Ratio | {sharpe} |
| Max Drawdown | {dd}% |
| Calmar Ratio | {calmar} |
| Win Rate | {wr}% |
| Profit Factor | {pf} |
| Total Trades | {trades} |

### Assessment
{performance_assessment}

### Key Insights
- {insight_1}
- {insight_2}
- {insight_3}

### Data Available for Further Analysis
- Equity curve data: {len(equity_curve)} points
- Monthly returns: {len(monthly_returns)} months
- Trade list: {len(trades)} trades

**Full API Response**: (attach if requested)
```

### For Optimization Results:

```markdown
## Optimization Result Analysis

**URL**: {user_url}
**Job ID**: {job_id}

### Configuration
- **Strategy**: {strategy_name}
- **Method**: {grid|bayesian}
- **Symbol/Interval**: {symbol} {interval}
- **Time Range**: {start_time} to {end_time}

### Best Result
- **Score**: {score}
- **Parameters**: {formatted_best_params}
- **Return**: {return}%
- **Sharpe**: {sharpe}
- **Max DD**: {dd}%

### Stability Analysis
- **Stability Score**: {stability_score}/1.0
- **Status**: {stable|unstable}
- **Variance**: {variance}

### Assessment
{optimization_assessment}
```

## Common Use Cases

### Case 1: Analyze Backtest Performance
**User input**: "Analyze http://localhost:3002/results/343"

**Actions**:
1. Extract job_id: 343
2. Call `GET /api/v1/backtest/jobs/343/report`
3. Parse response
4. Display formatted metrics
5. Provide performance assessment

### Case 2: Compare Multiple Results
**User input**: "Compare results 343 and 350"

**Actions**:
1. Fetch data for both jobs
2. Extract key metrics
3. Create comparison table
4. Highlight differences

### Case 3: Extract Trade Data
**User input**: "Get trades for result 343"

**Actions**:
1. Call `GET /api/v1/backtest/jobs/343/report` to get result_id
2. Call `GET /api/v1/backtest/results/{result_id}/trades`
3. Display trade list with analysis

### Case 4: Check Optimization Results
**User input**: "What's the best params from optimization 333?"

**Actions**:
1. Call `GET /api/v1/backtest/optimization/jobs/333/results`
2. Sort by score
3. Display top result with parameters

## Error Handling

If API call fails:

1. **Check backend status**: `curl http://localhost:8000/api/v1/strategies/`
2. **Invalid job ID**: Verify the ID exists in database
3. **Job not completed**: Check job status first
4. **Network error**: Ensure backend is running

## Notes

- **ID type**: Most `/results/{id}` URLs use `job_id`, not `result_id`
- **Percentage values**: API returns decimals (0.15 = 15%), display as percentages
- **Timestamps**: API returns ISO format, convert to readable dates
- **Large responses**: For trade lists with 100+ items, summarize first N trades
- **Cached data**: Frontend may cache data; API always returns fresh data

## Integration with Other Skills

This skill can be combined with:
- **optimize-strategy**: Extract optimization results for further analysis
- **Code analysis**: Use extracted parameters to analyze strategy code
- **Performance debugging**: Compare good vs bad results to identify issues
