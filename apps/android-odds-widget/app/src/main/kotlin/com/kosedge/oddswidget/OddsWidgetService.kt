package com.kosedge.oddswidget

import android.appwidget.AppWidgetManager
import android.content.Intent
import android.widget.RemoteViews
import android.widget.RemoteViewsService
import org.json.JSONArray
import org.json.JSONObject

class OddsWidgetService : RemoteViewsService() {
    override fun onGetViewFactory(intent: Intent): RemoteViewsFactory =
        OddsListFactory(applicationContext, intent.getIntExtra(AppWidgetManager.EXTRA_APPWIDGET_ID, 0))
}

private class OddsListFactory(
    private val context: android.content.Context,
    private val widgetId: Int
) : RemoteViewsService.RemoteViewsFactory {

    private val items = mutableListOf<GameRow>()

    override fun onCreate() {}

    override fun onDataSetChanged() {
        items.clear()
        val json = OddsPrefs.getOddsJson(context) ?: return
        try {
            val obj = JSONObject(json)
            val rows = obj.optJSONArray("rows") ?: JSONArray(json)
            val byGame = mutableMapOf<String, MutableMap<String, String>>()
            for (i in 0 until rows.length()) {
                val r = rows.optJSONObject(i) ?: continue
                val game = r.optString("game", "").ifBlank { "—" }
                val market = r.optString("market", "")
                val open = r.optString("open", "—")
                val best = r.optString("best", "—")
                val g = byGame.getOrPut(game) { mutableMapOf() }
                if (market.equals("Spread", true)) {
                    g["openLine"] = open
                    g["bestLine"] = best
                } else if (market.equals("Total", true)) {
                    g["openOU"] = open
                    g["bestOU"] = best
                }
            }
            byGame.forEach { (game, data) ->
                items.add(
                    GameRow(
                        game = game,
                        openLine = data["openLine"] ?: "—",
                        openOU = data["openOU"] ?: "—",
                        bestLine = data["bestLine"] ?: "—",
                        bestOU = data["bestOU"] ?: "—"
                    )
                )
            }
        } catch (_: Exception) {}
    }

    override fun onDestroy() {}

    override fun getCount(): Int = items.size

    override fun getViewAt(position: Int): RemoteViews {
        val r = items.getOrNull(position) ?: return RemoteViews(context.packageName, R.layout.widget_odds_item)
        val views = RemoteViews(context.packageName, R.layout.widget_odds_item)
        views.setTextViewText(R.id.item_game, r.game)
        views.setTextViewText(R.id.item_open, "O: ${r.openLine} / ${r.openOU}")
        views.setTextViewText(R.id.item_best, "B: ${r.bestLine} / ${r.bestOU}")
        return views
    }

    override fun getLoadingView(): RemoteViews? = null
    override fun getViewTypeCount(): Int = 1
    override fun getItemId(position: Int): Long = position.toLong()
    override fun hasStableIds(): Boolean = true

    private data class GameRow(val game: String, val openLine: String, val openOU: String, val bestLine: String, val bestOU: String)
}
