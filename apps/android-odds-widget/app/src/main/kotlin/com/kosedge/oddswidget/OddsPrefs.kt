package com.kosedge.oddswidget

import android.content.Context
import android.content.SharedPreferences

object OddsPrefs {
    private const val PREFS = "odds_widget"
    private const val KEY_JSON = "odds_json"
    private const val KEY_UPDATED = "updated_at"

    private fun prefs(context: Context): SharedPreferences =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun saveOddsJson(context: Context, json: String) {
        prefs(context).edit()
            .putString(KEY_JSON, json)
            .putLong(KEY_UPDATED, System.currentTimeMillis())
            .apply()
    }

    fun getOddsJson(context: Context): String? = prefs(context).getString(KEY_JSON, null)
    fun getUpdatedAt(context: Context): Long = prefs(context).getLong(KEY_UPDATED, 0L)
}
