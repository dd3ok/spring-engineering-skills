plugins {
    base
    alias(libs.plugins.boot) apply false
    alias(libs.plugins.dependency.management) apply false
    alias(libs.plugins.kotlin.jvm) apply false
    alias(libs.plugins.kotlin.spring) apply false
}
