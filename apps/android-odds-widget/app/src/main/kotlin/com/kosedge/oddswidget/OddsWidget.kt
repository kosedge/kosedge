package com.kosedge.oddswidget

import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.Context
import android.content.Intent
import android.widget.RemoteViews
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class OddsWidget : AppWidgetProvider() {

    override fun onUpdate(
        context: Context,
        appWidgetManager: AppWidgetManager,
        appWidgetIds: IntArray
    ) {
        for (id in appWidgetIds) {
            updateWidget(context, appWidgetManager, id)
        }
    }

    override fun onEnabled(context: Context) {
        OddsWorker.runOnce(context)
    }

    companion object {
        fun updateAllWidgets(context: Context) {
            val manager = AppWidgetManager.getInstance(context)
            val ids = manager.getAppWidgetIds(
                android.content.ComponentName(context, OddsWidget::class.java)
            )
            for (id in ids) updateWidget(context, manager, id)
        }

        private fun updateWidget(
            context: Context,
            manager: AppWidgetManager,
            widgetId: Int
        ) {
            val views = RemoteViews(context.packageName, R.layout.widget_odds)
            val json = OddsPrefs.getOddsJson(context)
            val updated = OddsPrefs.getUpdatedAt(context)
            views.setTextViewText(
                R.id.widget_updated,
                "Updated " + if (updated > 0) {
                    SimpleDateFormat("h:mm a", Locale.getDefault()).format(Date(updated))
                } else "—"
            )
            if (!json.isNullOrBlank()) {
                val svc = Intent(context, OddsWidgetService::class.java).apply {
                    putExtra(AppWidgetManager.EXTRA_APPWIDGET_ID, widgetId)
                }
                views.setRemoteAdapter(R.id.widget_list, svc)
            }
            manager.updateAppWidget(widgetId, views)
            manager.notifyAppWidgetViewDataChanged(widgetId, R.id.widget_list)
        }
    }
}
