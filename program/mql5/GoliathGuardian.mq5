//+------------------------------------------------------------------+
//|                                              MoneyMakerGuardian.mq5 |
//|                        MONEYMAKER Trading Ecosystem — Guardian EA    |
//|                                                                  |
//| Last line of defense: runs inside MT5 independently from the     |
//| Python bridge. Monitors MONEYMAKER positions and intervenes when     |
//| the external system is unreachable.                               |
//|                                                                  |
//| This EA does NOT place trades. It only:                           |
//|   1. Monitors heartbeat from the Python bridge                   |
//|   2. Manages emergency trailing stops when bridge is offline     |
//|   3. Hard-closes all positions on critical drawdown              |
//|   4. Auto-closes positions before weekend gap (Friday session)   |
//|   5. Logs all defensive actions to a local file                  |
//+------------------------------------------------------------------+
#property copyright   "MONEYMAKER Trading Ecosystem"
#property version     "1.00"
#property description "Guardian EA — independent safety net for MONEYMAKER positions"
#property strict

//+------------------------------------------------------------------+
//| Input Parameters                                                  |
//+------------------------------------------------------------------+

// --- Heartbeat ---
input int    InpHeartbeatTimeoutSec   = 30;     // Seconds without heartbeat → defensive mode
input string InpHeartbeatGlobalVar    = "MONEYMAKER_HEARTBEAT"; // GlobalVariable name for heartbeat

// --- Magic Number (must match Python bridge: 123456) ---
input int    InpMagicNumber           = 123456; // MONEYMAKER magic number

// --- Emergency Trailing Stop (active only when bridge is offline) ---
input bool   InpEmergencyTrailEnabled = true;   // Enable emergency trailing stop
input double InpTrailActivationPips   = 30.0;   // Pips in profit to activate trailing
input double InpTrailDistancePips     = 50.0;   // Trailing stop distance in pips

// --- Hard Drawdown Kill ---
input bool   InpDrawdownKillEnabled   = true;   // Enable hard drawdown kill
input double InpMaxDrawdownPct        = 10.0;   // Max drawdown % → close ALL positions
input double InpMaxDailyLossPct       = 2.0;    // Max daily loss % → close ALL positions

// --- Friday Session Close ---
input bool   InpFridayCloseEnabled    = true;   // Auto-close before weekend
input int    InpFridayCloseHour       = 21;     // Hour (server time) to close on Friday
input int    InpFridayCloseMinute     = 0;      // Minute to close on Friday

// --- Monitoring ---
input int    InpCheckIntervalSec      = 3;      // Check interval in seconds
input string InpLogFileName           = "MoneyMakerGuardian.log"; // Log file name

//+------------------------------------------------------------------+
//| Global State                                                      |
//+------------------------------------------------------------------+
bool     g_defensiveMode       = false;    // True when bridge heartbeat is stale
bool     g_drawdownKillFired   = false;    // True if drawdown kill already triggered this session
datetime g_lastCheckTime       = 0;        // Last check timestamp
datetime g_lastHeartbeat       = 0;        // Last valid heartbeat received
double   g_peakEquity          = 0.0;      // Session peak equity for drawdown calc
double   g_startBalance        = 0.0;      // Balance at EA start (for daily loss calc)
int      g_logHandle           = INVALID_HANDLE; // Log file handle

//+------------------------------------------------------------------+
//| Expert initialization                                             |
//+------------------------------------------------------------------+
int OnInit()
{
   // Open log file (append mode)
   g_logHandle = FileOpen(InpLogFileName, FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ | FILE_SHARE_WRITE);
   if(g_logHandle == INVALID_HANDLE)
   {
      // Try read+write for append
      g_logHandle = FileOpen(InpLogFileName, FILE_READ | FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_SHARE_READ | FILE_SHARE_WRITE);
      if(g_logHandle != INVALID_HANDLE)
         FileSeek(g_logHandle, 0, SEEK_END);
   }

   LogMessage("========================================");
   LogMessage("MoneyMakerGuardian EA initialized");
   LogMessage(StringFormat("Magic: %d | Heartbeat timeout: %ds", InpMagicNumber, InpHeartbeatTimeoutSec));
   LogMessage(StringFormat("Emergency trail: %s (activation: %.1f pips, distance: %.1f pips)",
              InpEmergencyTrailEnabled ? "ON" : "OFF", InpTrailActivationPips, InpTrailDistancePips));
   LogMessage(StringFormat("Drawdown kill: %s (max DD: %.1f%%, max daily loss: %.1f%%)",
              InpDrawdownKillEnabled ? "ON" : "OFF", InpMaxDrawdownPct, InpMaxDailyLossPct));
   LogMessage(StringFormat("Friday close: %s (%02d:%02d server time)",
              InpFridayCloseEnabled ? "ON" : "OFF", InpFridayCloseHour, InpFridayCloseMinute));

   // Initialize peak equity and start balance
   g_peakEquity  = AccountInfoDouble(ACCOUNT_EQUITY);
   g_startBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   g_lastCheckTime = TimeCurrent();

   // Set timer for periodic checks
   EventSetTimer(InpCheckIntervalSec);

   // Show status on chart
   UpdateChartComment();

   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization                                           |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   LogMessage("MoneyMakerGuardian EA stopped, reason: " + IntegerToString(reason));
   LogMessage("========================================");

   if(g_logHandle != INVALID_HANDLE)
   {
      FileClose(g_logHandle);
      g_logHandle = INVALID_HANDLE;
   }

   EventKillTimer();
   Comment("");
}

//+------------------------------------------------------------------+
//| Timer event — main guardian loop                                   |
//+------------------------------------------------------------------+
void OnTimer()
{
   datetime now = TimeCurrent();

   // Avoid running too frequently
   if(now - g_lastCheckTime < InpCheckIntervalSec)
      return;
   g_lastCheckTime = now;

   // --- Step 1: Check heartbeat ---
   CheckHeartbeat(now);

   // --- Step 2: Update peak equity ---
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity > g_peakEquity)
      g_peakEquity = equity;

   // --- Step 3: Hard drawdown kill (always active, independent of bridge) ---
   if(InpDrawdownKillEnabled && !g_drawdownKillFired)
      CheckDrawdownKill(equity);

   // --- Step 4: Friday session close ---
   if(InpFridayCloseEnabled)
      CheckFridayClose(now);

   // --- Step 5: Emergency trailing stop (only when bridge is offline) ---
   if(g_defensiveMode && InpEmergencyTrailEnabled)
      ManageEmergencyTrailingStops();

   // --- Update chart display ---
   UpdateChartComment();
}

//+------------------------------------------------------------------+
//| OnTick — also run checks on each tick for responsiveness          |
//+------------------------------------------------------------------+
void OnTick()
{
   // Delegate to timer logic, but skip if recently checked
   datetime now = TimeCurrent();
   if(now - g_lastCheckTime >= InpCheckIntervalSec)
      OnTimer();
}

//+------------------------------------------------------------------+
//| Check Python bridge heartbeat via GlobalVariable                  |
//+------------------------------------------------------------------+
void CheckHeartbeat(datetime now)
{
   bool wasDefensive = g_defensiveMode;

   if(!GlobalVariableCheck(InpHeartbeatGlobalVar))
   {
      // No heartbeat variable exists — bridge never connected or was restarted
      if(!g_defensiveMode)
      {
         g_defensiveMode = true;
         LogMessage("DEFENSIVE MODE ON: heartbeat variable not found");
      }
      return;
   }

   double heartbeatTimestamp = GlobalVariableGet(InpHeartbeatGlobalVar);
   datetime heartbeatTime = (datetime)heartbeatTimestamp;

   int ageSec = (int)(now - heartbeatTime);

   if(ageSec > InpHeartbeatTimeoutSec)
   {
      if(!g_defensiveMode)
      {
         g_defensiveMode = true;
         LogMessage(StringFormat("DEFENSIVE MODE ON: heartbeat stale by %d seconds (threshold: %d)",
                    ageSec, InpHeartbeatTimeoutSec));
      }
   }
   else
   {
      g_lastHeartbeat = heartbeatTime;
      if(g_defensiveMode)
      {
         g_defensiveMode = false;
         LogMessage(StringFormat("DEFENSIVE MODE OFF: bridge heartbeat restored (age: %ds)", ageSec));
      }
   }
}

//+------------------------------------------------------------------+
//| Hard drawdown / daily loss kill — close ALL MONEYMAKER positions     |
//+------------------------------------------------------------------+
void CheckDrawdownKill(double currentEquity)
{
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   if(balance <= 0) return;

   // --- Check drawdown from peak equity ---
   if(g_peakEquity > 0)
   {
      double drawdownPct = ((g_peakEquity - currentEquity) / g_peakEquity) * 100.0;

      if(drawdownPct >= InpMaxDrawdownPct)
      {
         LogMessage(StringFormat("DRAWDOWN KILL: equity %.2f, peak %.2f, drawdown %.2f%% >= %.2f%%",
                    currentEquity, g_peakEquity, drawdownPct, InpMaxDrawdownPct));
         CloseAllMoneyMakerPositions("DRAWDOWN_KILL");
         g_drawdownKillFired = true;
         return;
      }
   }

   // --- Check daily loss from start balance ---
   if(g_startBalance > 0)
   {
      double currentBalance = AccountInfoDouble(ACCOUNT_BALANCE);
      double unrealizedPnL  = currentEquity - currentBalance;
      double totalDayPnL    = (currentBalance - g_startBalance) + unrealizedPnL;
      double dailyLossPct   = 0.0;

      if(totalDayPnL < 0)
         dailyLossPct = MathAbs(totalDayPnL) / g_startBalance * 100.0;

      if(dailyLossPct >= InpMaxDailyLossPct)
      {
         LogMessage(StringFormat("DAILY LOSS KILL: day PnL %.2f, start balance %.2f, loss %.2f%% >= %.2f%%",
                    totalDayPnL, g_startBalance, dailyLossPct, InpMaxDailyLossPct));
         CloseAllMoneyMakerPositions("DAILY_LOSS_KILL");
         g_drawdownKillFired = true;
         return;
      }
   }
}

//+------------------------------------------------------------------+
//| Friday session close — avoid weekend gap risk                     |
//+------------------------------------------------------------------+
void CheckFridayClose(datetime now)
{
   MqlDateTime dt;
   TimeToStruct(now, dt);

   // day_of_week: 0=Sunday, 5=Friday
   if(dt.day_of_week != 5)
      return;

   if(dt.hour > InpFridayCloseHour ||
      (dt.hour == InpFridayCloseHour && dt.min >= InpFridayCloseMinute))
   {
      int moneymakerCount = CountMoneyMakerPositions();
      if(moneymakerCount > 0)
      {
         LogMessage(StringFormat("FRIDAY CLOSE: %02d:%02d server time, closing %d MONEYMAKER positions",
                    dt.hour, dt.min, moneymakerCount));
         CloseAllMoneyMakerPositions("FRIDAY_CLOSE");
      }
   }
}

//+------------------------------------------------------------------+
//| Emergency trailing stop — only when bridge is offline             |
//+------------------------------------------------------------------+
void ManageEmergencyTrailingStops()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;

      if(!PositionSelectByTicket(ticket)) continue;

      // Only manage MONEYMAKER positions
      if(PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;

      string symbol   = PositionGetString(POSITION_SYMBOL);
      long   posType  = PositionGetInteger(POSITION_TYPE);
      double openPx   = PositionGetDouble(POSITION_PRICE_OPEN);
      double currentPx = PositionGetDouble(POSITION_PRICE_CURRENT);
      double currentSL = PositionGetDouble(POSITION_SL);
      double currentTP = PositionGetDouble(POSITION_TP);

      double pipSize = GetPipSize(symbol);
      if(pipSize <= 0) continue;

      double trailActivation = InpTrailActivationPips * pipSize;
      double trailDistance    = InpTrailDistancePips * pipSize;

      if(posType == POSITION_TYPE_BUY)
      {
         double profitDistance = currentPx - openPx;
         if(profitDistance < trailActivation)
            continue;

         double newSL = currentPx - trailDistance;

         // Only move SL up, never down
         if(newSL > currentSL)
         {
            // Normalize to symbol's tick size
            newSL = NormalizeDouble(newSL, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS));

            MqlTradeRequest request = {};
            MqlTradeResult  result  = {};

            request.action   = TRADE_ACTION_SLTP;
            request.position = ticket;
            request.symbol   = symbol;
            request.sl       = newSL;
            request.tp       = currentTP;

            if(OrderSend(request, result))
            {
               if(result.retcode == TRADE_RETCODE_DONE)
               {
                  LogMessage(StringFormat("EMERGENCY TRAIL BUY: %s ticket %llu SL %.5f → %.5f (price: %.5f)",
                             symbol, ticket, currentSL, newSL, currentPx));
               }
            }
         }
      }
      else if(posType == POSITION_TYPE_SELL)
      {
         double profitDistance = openPx - currentPx;
         if(profitDistance < trailActivation)
            continue;

         double newSL = currentPx + trailDistance;

         // Only move SL down (for shorts), never up
         if(currentSL == 0 || newSL < currentSL)
         {
            newSL = NormalizeDouble(newSL, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS));

            MqlTradeRequest request = {};
            MqlTradeResult  result  = {};

            request.action   = TRADE_ACTION_SLTP;
            request.position = ticket;
            request.symbol   = symbol;
            request.sl       = newSL;
            request.tp       = currentTP;

            if(OrderSend(request, result))
            {
               if(result.retcode == TRADE_RETCODE_DONE)
               {
                  LogMessage(StringFormat("EMERGENCY TRAIL SELL: %s ticket %llu SL %.5f → %.5f (price: %.5f)",
                             symbol, ticket, currentSL, newSL, currentPx));
               }
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Close all positions with MONEYMAKER magic number                     |
//+------------------------------------------------------------------+
void CloseAllMoneyMakerPositions(string reason)
{
   int closed = 0;
   int failed = 0;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;

      if(!PositionSelectByTicket(ticket)) continue;

      if(PositionGetInteger(POSITION_MAGIC) != InpMagicNumber)
         continue;

      string symbol  = PositionGetString(POSITION_SYMBOL);
      long   posType = PositionGetInteger(POSITION_TYPE);
      double volume  = PositionGetDouble(POSITION_VOLUME);
      double profit  = PositionGetDouble(POSITION_PROFIT);

      MqlTradeRequest request = {};
      MqlTradeResult  result  = {};

      request.action   = TRADE_ACTION_DEAL;
      request.position = ticket;
      request.symbol   = symbol;
      request.volume   = volume;
      request.deviation = 50;  // Wide slippage for emergency close
      request.magic    = InpMagicNumber;
      request.comment  = "GUARDIAN:" + reason;

      if(posType == POSITION_TYPE_BUY)
      {
         request.type  = ORDER_TYPE_SELL;
         request.price = SymbolInfoDouble(symbol, SYMBOL_BID);
      }
      else
      {
         request.type  = ORDER_TYPE_BUY;
         request.price = SymbolInfoDouble(symbol, SYMBOL_ASK);
      }

      request.type_filling = ORDER_FILLING_IOC;

      if(OrderSend(request, result))
      {
         if(result.retcode == TRADE_RETCODE_DONE)
         {
            LogMessage(StringFormat("CLOSED %s ticket %llu | %s %.2f lots | PnL: %.2f | Reason: %s",
                       symbol, ticket, (posType == POSITION_TYPE_BUY ? "BUY" : "SELL"),
                       volume, profit, reason));
            closed++;
         }
         else
         {
            LogMessage(StringFormat("CLOSE FAILED %s ticket %llu | retcode: %d | %s",
                       symbol, ticket, result.retcode, result.comment));
            failed++;
         }
      }
      else
      {
         LogMessage(StringFormat("CLOSE ERROR %s ticket %llu | OrderSend failed", symbol, ticket));
         failed++;
      }
   }

   LogMessage(StringFormat("%s complete: %d closed, %d failed", reason, closed, failed));

   // Also cancel any pending MONEYMAKER orders
   CancelAllMoneyMakerPendingOrders(reason);
}

//+------------------------------------------------------------------+
//| Cancel all pending orders with MONEYMAKER magic number               |
//+------------------------------------------------------------------+
void CancelAllMoneyMakerPendingOrders(string reason)
{
   int cancelled = 0;

   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0) continue;

      if(OrderGetInteger(ORDER_MAGIC) != InpMagicNumber)
         continue;

      MqlTradeRequest request = {};
      MqlTradeResult  result  = {};

      request.action = TRADE_ACTION_REMOVE;
      request.order  = ticket;

      if(OrderSend(request, result))
      {
         if(result.retcode == TRADE_RETCODE_DONE)
         {
            LogMessage(StringFormat("CANCELLED pending order %llu | Reason: %s", ticket, reason));
            cancelled++;
         }
      }
   }

   if(cancelled > 0)
      LogMessage(StringFormat("Cancelled %d pending orders (%s)", cancelled, reason));
}

//+------------------------------------------------------------------+
//| Count open positions with MONEYMAKER magic number                    |
//+------------------------------------------------------------------+
int CountMoneyMakerPositions()
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(!PositionSelectByTicket(ticket)) continue;
      if(PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
         count++;
   }
   return count;
}

//+------------------------------------------------------------------+
//| Get pip size for a symbol                                          |
//+------------------------------------------------------------------+
double GetPipSize(string symbol)
{
   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);

   // Standard forex: 5 digits → 0.0001, 3 digits → 0.01
   if(digits == 5 || digits == 4)
      return 0.0001;
   if(digits == 3 || digits == 2)
      return 0.01;
   if(digits == 1)
      return 0.1;
   if(digits == 0)
      return 1.0;

   // Fallback
   return SymbolInfoDouble(symbol, SYMBOL_POINT) * 10.0;
}

//+------------------------------------------------------------------+
//| Log message to file and Experts tab                               |
//+------------------------------------------------------------------+
void LogMessage(string message)
{
   string timestamp = TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS);
   string logLine   = timestamp + " | " + message;

   // Print to MT5 Experts tab
   Print("[MoneyMakerGuardian] ", message);

   // Write to log file
   if(g_logHandle != INVALID_HANDLE)
   {
      FileWriteString(g_logHandle, logLine + "\n");
      FileFlush(g_logHandle);
   }
}

//+------------------------------------------------------------------+
//| Update chart comment with guardian status                          |
//+------------------------------------------------------------------+
void UpdateChartComment()
{
   double equity  = AccountInfoDouble(ACCOUNT_EQUITY);
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   int    moneymakerPos = CountMoneyMakerPositions();

   double drawdownPct = 0.0;
   if(g_peakEquity > 0)
      drawdownPct = ((g_peakEquity - equity) / g_peakEquity) * 100.0;

   double dailyPnL = 0.0;
   if(g_startBalance > 0)
      dailyPnL = (balance - g_startBalance) + (equity - balance);

   string mode = g_defensiveMode ? "!! DEFENSIVE !!" : "MONITORING";
   if(g_drawdownKillFired) mode = "!! KILL FIRED !!";

   string heartbeatAge = "N/A";
   if(g_lastHeartbeat > 0)
   {
      int age = (int)(TimeCurrent() - g_lastHeartbeat);
      heartbeatAge = IntegerToString(age) + "s ago";
   }

   string text = "";
   text += "╔══════════════════════════════════╗\n";
   text += "║     MONEYMAKER GUARDIAN EA v1.00     ║\n";
   text += "╠══════════════════════════════════╣\n";
   text += StringFormat("║ Mode:        %-19s ║\n", mode);
   text += StringFormat("║ Heartbeat:   %-19s ║\n", heartbeatAge);
   text += StringFormat("║ Positions:   %-19d ║\n", moneymakerPos);
   text += StringFormat("║ Equity:      %-19.2f ║\n", equity);
   text += StringFormat("║ Peak Equity: %-19.2f ║\n", g_peakEquity);
   text += StringFormat("║ Drawdown:    %-18.2f%% ║\n", drawdownPct);
   text += StringFormat("║ Day PnL:     %-19.2f ║\n", dailyPnL);
   text += "╚══════════════════════════════════╝\n";

   Comment(text);
}
//+------------------------------------------------------------------+
