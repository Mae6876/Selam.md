//+------------------------------------------------------------------+
//| ExportBars.mq5 — eksport bar TERTUTUP ke CSV untuk market_story.py|
//| Hasil: <TerminalData>\MQL5\Files\<SIMBOL>_<TF>.csv                |
//+------------------------------------------------------------------+
#property script_show_inputs
input string          InpSymbol = "XAUUSD";
input ENUM_TIMEFRAMES InpTF     = PERIOD_M15;
input int             InpBars   = 20000;

void OnStart()
{
   MqlRates r[];
   ArraySetAsSeries(r, false);
   int n = CopyRates(InpSymbol, InpTF, 0, InpBars, r);
   if(n <= 1) { Print("CopyRates gagal: ", GetLastError()); return; }
   int dg = (int)SymbolInfoInteger(InpSymbol, SYMBOL_DIGITS);
   string f = InpSymbol + "_" + EnumToString(InpTF) + ".csv";
   int h = FileOpen(f, FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   if(h == INVALID_HANDLE) { Print("FileOpen gagal: ", GetLastError()); return; }
   FileWrite(h, "time", "open", "high", "low", "close", "tick_volume");
   for(int i = 0; i < n - 1; i++)   // n-1: buang bar yang masih terbentuk
      FileWrite(h, TimeToString(r[i].time, TIME_DATE | TIME_MINUTES),
                DoubleToString(r[i].open, dg), DoubleToString(r[i].high, dg),
                DoubleToString(r[i].low, dg),  DoubleToString(r[i].close, dg),
                (string)r[i].tick_volume);
   FileClose(h);
   Print("Eksport siap: ", f, " (", n - 1, " bar)");
}
