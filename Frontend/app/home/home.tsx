
import React from "react";

export default function Home() {
    return (
        <div className="min-h-screen flex flex-col justify-center items-center bg-white">
            <div className="w-full max-w-2xl text-center py-16">
                <h1 className="text-4xl md:text-5xl font-bold mb-4">
                    Attack Surface Management Tool
                </h1>
                <p className="text-xl text-gray-600 mb-8">
                    Discover, monitor, and secure your digital assets in real time.
                </p>
                <a
                    href="/dashboard"
                    className="inline-block bg-blue-600 text-white px-8 py-3 rounded-lg text-lg font-semibold hover:bg-blue-700 transition"
                >
                    Get Started
                </a>
            </div>
            <div className="mt-16 w-full text-center">
                <h2 className="text-2xl font-semibold mb-4">Key Features</h2>
                <div className="flex flex-wrap justify-center gap-8 mt-4">
                    <div className="max-w-xs">
                        <h3 className="text-lg font-bold mb-2">Asset Discovery</h3>
                        <p className="text-gray-600 text-sm">
                            Automatically find and inventory your internet-facing assets.
                        </p>
                    </div>
                    <div className="max-w-xs">
                        <h3 className="text-lg font-bold mb-2">Continuous Monitoring</h3>
                        <p className="text-gray-600 text-sm">
                            Get alerts on new exposures and changes to your attack surface.
                        </p>
                    </div>
                    <div className="max-w-xs">
                        <h3 className="text-lg font-bold mb-2">Risk Assessment</h3>
                        <p className="text-gray-600 text-sm">
                            Prioritize vulnerabilities and focus on what matters most.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
