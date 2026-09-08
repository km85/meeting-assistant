package com.krishna.meetingassistant

import android.app.Application
import android.content.Context

class MeetingAssistantApp : Application() {
    companion object {
        var instance: MeetingAssistantApp? = null
    }

    override fun onCreate() {
        super.onCreate()
        instance = this
    }
}
